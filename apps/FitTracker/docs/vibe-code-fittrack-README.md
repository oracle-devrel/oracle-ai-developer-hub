# Vibe Coding with Oracle 23ai: FitTrack Builds

> Two implementations of the same fitness gamification platform — one prepared in advance, one built live during our webinar — demonstrating AI-assisted development with Oracle's JSON Duality Views.

**Webinar Recording**: [LinkedIn Event](https://www.linkedin.com/events/7411444379934031872/)

---

## What's Inside

This repository contains two complete implementations of **FitTrack**, a gamified fitness platform that rewards physical activity with sweepstakes entries:

| Folder | Build | Lines of Code | Description |
|--------|-------|---------------|-------------|
| `/FitTracker` | Pre-session | ~1,400 | Prepared implementation with comprehensive documentation |
| `/Fit_Tracker` | Live session | ~3,150 | Built during the webinar with audience participation |

Both implementations target the same PRD (Product Requirements Document) and demonstrate:

- **Oracle 23ai JSON Duality Views** for document-style access over relational tables
- **Python 3.12 + FastAPI** async backend
- **No ORM** — direct `python-oracledb` driver usage
- **Repository pattern** for clean data access abstraction

---

## Key Differences Between Builds

### Database Schema Approach

| Aspect | FitTracker (Pre-session) | Fit_Tracker (Live) |
|--------|--------------------------|---------------------|
| Migration files | 1 combined file | 2 separate files |
| Schema size | 17.8 KB | 14.5 KB + 10.3 KB |
| Duality Views | Embedded in schema | Separate migration |
| Separation of concerns | Tables + views together | Tables first, then views |

**Insight**: The live session naturally evolved toward better separation — relational tables in one migration, JSON Duality Views in another. This mirrors how you'd actually deploy: schema first, then the document API layer.

### Code Volume

| Metric | FitTracker | Fit_Tracker |
|--------|------------|-------------|
| Python LOC | ~1,394 | ~3,157 |
| Repositories | Base + stubs | 12 complete |
| API Routes | Scaffolded | Fully implemented |
| Test Factories | Basic | Complete set |

**Insight**: The live build is more complete — we had time to flesh out all the repository implementations, route handlers, and test factories. The pre-session build focused on architecture and documentation.

### Implementation Completeness

**FitTracker (Pre-session)**:
- ✅ Comprehensive PRD (2,060 lines)
- ✅ 7-checkpoint implementation plan
- ✅ Complete CLAUDE.md context file
- ✅ Database schema with all tables
- ⏳ Stub implementations for routes/repos

**Fit_Tracker (Live)**:
- ✅ Working API endpoints
- ✅ All 12 repositories implemented
- ✅ JSON Duality Views in separate migration
- ✅ Test factories for all entities
- ✅ Development test page (devtools/)
- ✅ Docker Compose with full stack

---

## Architecture Overview

Both builds share the same clean architecture:

```
src/fittrack/
├── api/
│   ├── routes/          # FastAPI endpoint modules
│   └── schemas/         # Pydantic request/response models
├── services/            # Business logic layer
├── repositories/        # Data access (Oracle + JSON Duality Views)
├── models/              # Domain models and enums
├── workers/             # Background job processors (Redis Queue)
└── core/                # Config, database, exceptions
```

### Tech Stack

- **Backend**: Python 3.12, FastAPI, Uvicorn
- **Database**: Oracle 23ai Free with JSON Duality Views
- **Cache/Queue**: Redis 7
- **Fitness Data**: Terra API (Apple Health, Google Fit, Fitbit)
- **Auth**: JWT (HS256 dev, RS256 prod)

---

## JSON Duality Views in Action

The core innovation demonstrated in both builds is Oracle's JSON Duality Views — storing data relationally while accessing it as documents:

```python
# Traditional relational INSERT
cursor.execute("""
    INSERT INTO users (id, email, password_hash, role, status)
    VALUES (:id, :email, :hash, :role, :status)
""", params)

# With JSON Duality View - same table, document API
cursor.execute("""
    INSERT INTO users_dv (data) VALUES (:1)
""", [json.dumps({
    "_id": user_id,
    "email": email,
    "passwordHash": password_hash,
    "role": "user",
    "status": "pending"
})])
```

**Why this matters**:
- Document flexibility for developers
- Relational integrity for the database
- No sync lag between document and relational views
- Single source of truth

---

## Running the Projects

### Prerequisites

- Docker & Docker Compose
- Python 3.12+
- Oracle 23ai Free (runs in Docker)

### Quick Start (either project)

```bash
cd FitTracker  # or Fit_Tracker

# First-time setup
make setup

# Start all services (Oracle, Redis, API, Workers)
make dev

# Run tests
make test

# Seed sample data
make db-seed
```

### Key Endpoints

Both builds expose the same API surface:

| Endpoint | Purpose |
|----------|---------|
| `GET /api/v1/health` | Liveness/readiness checks |
| `POST /api/v1/users` | User registration |
| `GET /api/v1/users/{id}` | User profile |
| `POST /api/v1/activities` | Log fitness activity |
| `GET /api/v1/drawings` | List sweepstakes |
| `POST /api/v1/tickets` | Purchase entry |

---

## What We Learned

### 1. AI-Assisted Development is Iterative

The pre-session build had better documentation. The live build had more working code. Neither is "better" — they represent different phases of the same development cycle.

### 2. JSON Duality Views Change the Game

No more choosing between document flexibility and relational integrity. No more syncing document stores with relational databases. The database handles both views natively.

### 3. Separation Matters

The live session's decision to split migrations (tables → duality views) wasn't planned — it emerged naturally. That's a sign of good architecture: the right structure becomes obvious as you build.

### 4. Context Files Are Essential

Both builds include comprehensive `CLAUDE.md` files. These aren't documentation for humans — they're context for AI assistants. Good context files make AI-assisted development dramatically more effective.

---

## The FitTrack Concept

**What it does**: Users connect fitness trackers, earn points from physical activity, spend points on sweepstakes tickets, compete on tiered leaderboards.

**Competition Tiers**: 31 brackets based on demographics (age, sex, fitness level) ensure fair competition:
- `M-18-29-BEG` (Male, 18-29, Beginner)
- `F-40-49-ADV` (Female, 40-49, Advanced)
- `OPEN` (All users)

**Point System**:
- 10 pts per 1,000 steps (max 20K/day)
- 1-3 pts per active minute (by intensity)
- 50 pts per workout (max 3/day)
- Daily cap: 1,000 points (anti-gaming)

**Sweepstakes**: Daily, weekly, monthly, annual drawings with CSPRNG selection and full audit trails.

---

## Resources

- **Oracle JSON Duality Views**: [Documentation](https://docs.oracle.com/en/database/oracle/oracle-database/23/jsnvu/)
- **FastAPI**: [Documentation](https://fastapi.tiangolo.com/)
- **python-oracledb**: [Documentation](https://python-oracledb.readthedocs.io/)
- **Terra API**: [Documentation](https://docs.tryterra.co/)

---

## Questions?

Reach out on [LinkedIn](https://www.linkedin.com/in/rickhoulihan/) or open an issue in this repo.

---

*Built with Oracle 23ai, FastAPI, and a lot of vibe coding.*
