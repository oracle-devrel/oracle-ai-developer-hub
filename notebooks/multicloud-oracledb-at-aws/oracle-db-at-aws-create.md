# Creating and Connecting to Oracle Database on AWS RDS

This guide provides step-by-step instructions for creating an Oracle Database instance on Amazon RDS (Relational Database Service) and connecting to it from your applications.

## Prerequisites

Before you begin, ensure you have:

1. **AWS Account** - An active AWS account with appropriate permissions
2. **AWS Management Console Access** - To navigate RDS dashboard
3. **AWS CLI (Optional)** - For command-line database creation
4. **Network Access** - Proper VPC and security group configuration
5. **Oracle Client Tools (Optional)** - For local connections (SQL*Plus, SQL Developer)

## Step 1: Sign In to AWS Console

1. Open the [AWS Management Console](https://aws.amazon.com/console/)
2. Sign in with your AWS account credentials
3. Select your desired region (e.g., us-east-1, us-west-2)
4. Search for and navigate to **RDS (Relational Database Service)**

## Step 2: Create an RDS Oracle Database Instance

### Using AWS Management Console

1. **Open RDS Dashboard**
   - Go to Services → RDS → Databases
   - Click **Create database**

2. **Choose Database Creation Method**
   - Select **Standard create** (for more control)
   - Or **Easy create** (for quick setup with defaults)

3. **Select Engine**
   - Engine type: **Oracle**
   - Edition: Choose one of:
     - Oracle Database 19c (recommended for latest features)
     - Oracle Database 21c (latest version)
     - Oracle Database 12c Release 2 (for legacy compatibility)
   - License: Choose **License included** or **Bring your own license (BYOL)**

4. **Database Instance Class**
   - Instance class: Select based on workload:
     - **db.t3.micro** - For testing/development (Free Tier eligible)
     - **db.t3.small** - Light workloads
     - **db.t3.medium** - Small production workloads
     - **db.m5.large** - Production workloads
     - Larger sizes for heavy production use
   - Multi-AZ: Enable for production (High Availability)
   - Storage type: **gp3** (General Purpose SSD) or **io1** (IOPS-optimized)
   - Allocated storage: 100 GB minimum, 20+ GB recommended

5. **Database Identifier and Credentials**
   - DB instance identifier: `oracle-dev` (or your preferred name)
   - Master username: `admin` (or custom username)
   - Master password: Create a strong password
     - Minimum 8 characters
     - Mix of uppercase, lowercase, numbers, special characters
   - **Save password in AWS Secrets Manager** (recommended)

6. **Connectivity**
   - VPC: Select your VPC (default or custom)
   - DB subnet group: Create new or use existing
   - Public accessibility: 
     - **No** - For internal applications only
     - **Yes** - For external connections (requires security group rules)
   - Availability Zone: Select preferred AZ or let AWS choose
   - Security group: Create new or use existing
     - Default security group is created automatically

7. **Database Authentication**
   - Authentication: **Password authentication** (standard)
   - Optional: Enable IAM database authentication for additional security

8. **Advanced Settings** (Optional but recommended)
   - Database name: `ORCL` (or your custom name)
   - Port: `1521` (default Oracle port)
   - Parameter group: Default or custom
   - Option group: Default or custom
   - Backup retention: 7 days (adjust as needed)
   - Backup window: Select preferred maintenance window
   - Enable encryption: Yes (Recommended)
   - KMS key: Use AWS managed key or custom key
   - Enable Enhanced Monitoring: Yes (for production)
   - Logs to publish: Alert log, audit log, trace file

9. **Review and Create**
   - Review all settings
   - Click **Create database**
   - Wait for database creation (typically 5-10 minutes)

### Using AWS CLI

```bash
aws rds create-db-instance \
  --db-instance-identifier oracle-dev \
  --db-instance-class db.t3.small \
  --engine oracle-ee \
  --engine-version 19.0.0.0 \
  --master-username admin \
  --master-user-password MySecurePassword123! \
  --allocated-storage 100 \
  --db-name ORCL \
  --port 1521 \
  --vpc-security-group-ids sg-xxxxxxxx \
  --publicly-accessible true \
  --backup-retention-period 7
```

## Step 3: Configure Security Groups

### For Internal Access Only

1. Open EC2 → Security Groups
2. Find the RDS security group
3. **Inbound rules** - Add rule:
   - Type: Custom TCP
   - Port range: 1521 (Oracle default)
   - Source: Security group of application EC2 instances
   - Description: "Oracle RDS access from application"

### For External Access

1. Open EC2 → Security Groups
2. Find the RDS security group
3. **Inbound rules** - Add rule:
   - Type: Custom TCP
   - Port range: 1521
   - Source: Your IP address (0.0.0.0/0 for any - not recommended for production)
   - Description: "Oracle RDS access from external"

## Step 4: Retrieve Connection Details

1. In RDS Dashboard, click your Oracle instance
2. **Endpoint & Port** section shows:
   - **Endpoint**: `oracle-dev.xxxxxxxx.us-east-1.rds.amazonaws.com`
   - **Port**: `1521`
3. Save these details for connection strings

## Step 5: Connect to Oracle Database

### Option A: Using SQL*Plus (Command Line)

```bash
# Install Oracle Instant Client (if not already installed)
# For macOS with homebrew:
brew install oracle-instantclient

# For Linux, download from Oracle website

# Connect to database
sqlplus admin@oracle-dev.xxxxxxxx.us-east-1.rds.amazonaws.com:1521/ORCL

# When prompted, enter your master password
```

### Option B: Using SQL Developer (GUI)

1. Download [Oracle SQL Developer](https://www.oracle.com/database/sqldeveloper/technologies/download/)
2. Create new connection:
   - Connection Name: `AWS-Oracle-Dev`
   - Username: `admin`
   - Password: Your master password
   - Hostname: `oracle-dev.xxxxxxxx.us-east-1.rds.amazonaws.com`
   - Port: `1521`
   - Service name: `ORCL`
3. Test connection → Connect

### Option C: Using Python (cx_Oracle)

```python
import cx_Oracle

# Database connection details
db_config = {
    'user': 'admin',
    'password': 'YourMasterPassword',
    'host': 'oracle-dev.xxxxxxxx.us-east-1.rds.amazonaws.com',
    'port': 1521,
    'service_name': 'ORCL'
}

# Build connection string
connection_string = (
    f"{db_config['user']}/{db_config['password']}@"
    f"{db_config['host']}:{db_config['port']}/"
    f"{db_config['service_name']}"
)

# Connect to database
try:
    connection = cx_Oracle.connect(connection_string)
    print("✓ Connected to Oracle Database successfully")
    
    # Test query
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM v$version WHERE ROWNUM = 1")
    print(cursor.fetchone())
    
    cursor.close()
    connection.close()
except cx_Oracle.DatabaseError as e:
    print(f"✗ Connection failed: {e}")
```

### Option D: Using Node.js (oracledb)

```javascript
const oracledb = require('oracledb');

async function connectDB() {
  try {
    const connection = await oracledb.getConnection({
      user: 'admin',
      password: 'YourMasterPassword',
      connectString: 'oracle-dev.xxxxxxxx.us-east-1.rds.amazonaws.com:1521/ORCL'
    });

    console.log("✓ Connected to Oracle Database successfully");

    // Test query
    const result = await connection.execute(
      'SELECT * FROM v$version WHERE ROWNUM = 1'
    );
    console.log(result.rows);

    await connection.close();
  } catch (error) {
    console.error("✗ Connection failed:", error);
  }
}

connectDB();
```

## Step 6: Load Sample Data

### Create Sample Table

```sql
CREATE TABLE documents (
  id NUMBER PRIMARY KEY,
  title VARCHAR2(255),
  content CLOB,
  category VARCHAR2(100),
  created_date TIMESTAMP DEFAULT SYSDATE
);
```

### Insert Sample Data

```sql
INSERT INTO documents (id, title, content, category)
VALUES (1, 'Machine Learning Basics', 'Content about ML...', 'AI');

INSERT INTO documents (id, title, content, category)
VALUES (2, 'Cloud Database Solutions', 'Content about cloud...', 'Cloud');

COMMIT;
```

## Step 7: Enable AWS Secrets Manager Integration (Optional)

### Store Database Credentials Securely

1. Go to **AWS Secrets Manager**
2. Click **Store a new secret**
3. Secret type: **Credentials for RDS database**
4. Select your RDS instance
5. Username: `admin`
6. Password: Your master password
7. Secret name: `oracle-dev-credentials`
8. Click **Store**

### Access from Application Code

```python
import json
import boto3

secrets_client = boto3.client('secretsmanager')

secret_response = secrets_client.get_secret_value(
    SecretId='oracle-dev-credentials'
)

secret = json.loads(secret_response['SecretString'])

# Use in connection
db_config = {
    'user': secret['username'],
    'password': secret['password'],
    'host': secret['host'],
    'port': secret['port'],
    'service_name': secret['dbname']
}
```

## Step 8: Monitor and Manage

### CloudWatch Monitoring

1. Open RDS Dashboard
2. Select your database instance
3. View **Monitoring** tab:
   - CPU Utilization
   - Database Connections
   - Storage Space
   - Network I/O
   - Read/Write Latency

### Backup and Restore

1. Click your database instance
2. **Maintenance & backups**:
   - Automated backups are enabled by default
   - Create manual snapshots before major changes
   - Define backup retention period

### Modify Instance

1. Click your database instance
2. Click **Modify**:
   - Change instance class for performance
   - Increase storage
   - Enable Multi-AZ
   - Change backup retention
   - Update security settings
3. Click **Continue** and **Apply immediately** or schedule change

## Troubleshooting

### Connection Issues

**Error: "Network error – could not resolve service name"**
- Verify RDS endpoint is correct
- Check security group allows port 1521
- Ensure application is in same VPC or has network connectivity

**Error: "ORA-12514: TNS:listener does not currently know of service requested"**
- Verify database name (ORCL) is correct
- Check RDS instance is in Available state
- Wait for RDS to finish initialization

**Error: "ORA-01017: invalid username/password"**
- Verify master username and password
- Check for special characters in password
- Reset password from RDS console if needed

### Performance Issues

- Check CloudWatch metrics for CPU and I/O
- Review slow query logs
- Consider upgrading instance class
- Enable Enhanced Monitoring for detailed metrics

## Best Practices

1. **Security**
   - Use strong passwords (minimum 8 characters, mixed case)
   - Enable encryption at rest and in transit
   - Use Security Groups to restrict access
   - Consider IAM database authentication
   - Store credentials in AWS Secrets Manager

2. **Backup & Recovery**
   - Enable automated backups with sufficient retention
   - Create snapshots before major changes
   - Test restore procedures regularly
   - Use Multi-AZ for production environments

3. **Performance**
   - Choose appropriate instance class for workload
   - Use gp3 storage for general purpose workloads
   - Monitor CloudWatch metrics regularly
   - Enable Enhanced Monitoring for production

4. **Cost Optimization**
   - Use db.t3 instances for variable workloads
   - Disable unused features
   - Use Reserved Instances for predictable workloads
   - Set appropriate backup retention periods

5. **Maintenance**
   - Schedule maintenance windows during off-peak hours
   - Keep database software up to date
   - Monitor for deprecated features
   - Review AWS notifications for database updates

## Additional Resources

- [AWS RDS Oracle Documentation](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Oracle.html)
- [RDS Oracle Pricing](https://aws.amazon.com/rds/oracle/pricing/)
- [Oracle Database on AWS FAQs](https://aws.amazon.com/rds/oracle/faqs/)
- [RDS Best Practices](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/CHAP_BestPractices.html)

## Next Steps

Once your Oracle database is running on AWS RDS:

1. **Load Data** - Migrate existing data or load sample datasets
2. **Configure Networking** - Set up VPC endpoints for secure access
3. **Enable Monitoring** - Set up CloudWatch alarms for key metrics
4. **Implement Backups** - Configure automated backup strategy
5. **Create Indexes** - Optimize query performance for your workload
6. **Use with AI Tools** - Integrate with the Oracle RAG agents notebook for semantic search

For more information on semantic similarity search using embeddings, see the [Oracle RAG Agents notebook](../rag-aiagent-chatbot/RAGChatbotwithAgentDevelopmentKit.ipynb).
