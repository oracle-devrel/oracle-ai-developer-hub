# Jakarta EE on Virtual Threads with Helidon MP

This repository reproduces the code and load-test scenarios from the Jakarta EE on Virtual Threads presentation. It contains one Helidon MP 4.4 credit-decision service running familiar Jakarta REST and CDI code on Java 21 virtual threads.

The two demo paths make the runtime story concrete:

- `POST /credit-decisions/evaluate` retains the 65 ms simulated blocking workflow and skips persistence. Use it to isolate virtual-thread scheduling.
- `POST /credit-decisions` runs the same workflow and persists the result to Oracle when OBaaS injects the datasource. Use it to observe the additional JDBC-backed insert and transaction work.

## Repository layout

```text
helidon-credit-service/  Helidon MP application and OBaaS values
load-tests/              k6 scripts for the two presentation scenarios
api/                     OpenAPI contract and sample requests
deploy/obaas/            OBaaS deployment and gateway instructions
```

## Prerequisites

- Java 21
- Maven 3.9+
- k6 for the load tests
- Docker only when building a container image
- An OBaaS environment with Oracle Autonomous Database and SigNoz for the full deployment walkthrough. Start with Oracle's [OBaaS setup guide](https://oracle.github.io/microservices-backend/obaas/docs/setup/) to install or access an environment.

## Build and run locally

Build the project from the repository root:

```bash
mvn clean package
```

Run the service:

```bash
java -jar helidon-credit-service/target/helidon-credit-service.jar
```

Without an OBaaS-injected datasource, the service uses an embedded H2 database in Oracle compatibility mode. That lets attendees run both request paths locally; the full Oracle and SigNoz walkthrough requires OBaaS.

Verify the service:

```bash
curl -s http://localhost:8080/health/simple | jq
curl -s -X POST http://localhost:8080/credit-decisions/evaluate \
  -H 'content-type: application/json' \
  -d @api/sample-requests/approved.json | jq
```

## Service API

```text
POST /credit-decisions            Evaluate and persist a decision when Oracle is configured
POST /credit-decisions/evaluate   Evaluate without persistence
GET  /credit-decisions/{id}       Fetch one decision
GET  /credit-decisions/customer/{id}
GET  /health/simple
```

The shared contract is [api/openapi.yaml](api/openapi.yaml).

## Reproduce Demo 3: virtual-thread sweet spot

This scenario removes the database from the request path while retaining the 65 ms simulated blocking workflow:

```bash
k6 run \
  -e BASE_URL=http://localhost:8080 \
  -e VUS=250 \
  -e SLEEP=0 \
  -e DURATION=300s \
  load-tests/credit-decision-evaluate.js
```

Expected signals:

- about 250 active virtual threads during the load window;
- no pinned virtual threads or submit failures;
- successful HTTP checks and a stable request rate.

## Reproduce Demo 4: database-backed request work

Run this against an OBaaS deployment with Oracle configured:

```bash
k6 run \
  -e BASE_URL=http://localhost:8080 \
  -e VUS=250 \
  -e SLEEP=0 \
  -e DURATION=300s \
  load-tests/credit-decision.js
```

The DB-backed path performs the same simulated waits as Demo 3, then writes a decision through Helidon Data, Jakarta Persistence, and Oracle JDBC. It should complete fewer iterations than the no-database path because each request now includes database and transaction work.

Compare the k6 summaries using the same target, VUs, duration, and client pacing. In the presentation run, the no-database scenario completed 590,701 requests at 1,968 requests/s; the DB-backed scenario completed 405,411 requests at 1,351 requests/s, both with zero HTTP failures.

## Inspect the results in SigNoz

After each scenario, use the same time window in the following dashboards. The goal is to connect the k6 client results to the Java runtime and, for Demo 4, to the database.

### Helidon JVM Details

- **Requests Per Second:** confirm the sustained server-side rate and compare the two runs.
- **Helidon Virtual Threads:** during both 250-VU runs, active virtual threads should be close to the offered load; pinned virtual threads and submit failures should remain at zero.
- **CPU and Memory Usage:** use these as context for the load rather than treating them as the sole explanation for a throughput change.

### Service and trace views

- **Helidon MP Details** or the service overview: inspect request rate, latency percentiles, and error rate.
- **Traces:** open a `POST /credit-decisions` trace from Demo 4. It should show the Oracle database work beneath the request span.
- **Logs:** move from that trace to the correlated application log line when explaining what the service did.

### Oracle Database Details

- **User commits** and **execute counts:** the DB-backed run should make these rise; the presentation run showed roughly one user commit per successful create request.
- **Active sessions** and **system wait classes:** use these to see whether database work is active or visibly constrained.
- **Top SQL:** distinguish application SQL from database monitoring and housekeeping queries before drawing conclusions.

For the two scenarios, expect active virtual threads to remain close to the requested 250-user load while the DB-backed path has a lower request rate and higher latency. In the presentation run, the no-database scenario completed 590,701 requests at 1,968 requests/s; the DB-backed scenario completed 405,411 requests at 1,351 requests/s, both with zero HTTP failures.

The result is not a claim that virtual threads make database work faster. They make Java waiting cheaper. Persistence still adds JDBC, network, SQL, and transaction-completion cost to each request.

## Deploy to OBaaS

Use [deploy/obaas/README.md](deploy/obaas/README.md) to build the image, deploy the Helm chart, expose the service through APISIX, and locate the SigNoz credentials in the cluster.
