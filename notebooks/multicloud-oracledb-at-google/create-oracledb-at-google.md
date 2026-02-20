# Oracle Autonomous Database on Google Cloud Platform

## Introduction

This guide provides comprehensive instructions for deploying an **Oracle Autonomous Database on Google Cloud Platform (GCP)**. We cover both the Google Cloud Console UI and the Google Cloud Command Line Interface (CLI) approaches, enabling you to choose the method that best fits your workflow.

### What You'll Learn

- Authenticate and navigate the Google Cloud Console
- Create and configure Google Cloud infrastructure components (Projects, VPCs, Subnets)
- Deploy Oracle Autonomous Database instances on Google Cloud
- Set up secure access through firewall rules and Compute Engine VMs
- Configure database connections and networking
- Access your database from various applications (Python, Java, Node.js, and more)
- Monitor and manage your Oracle Database deployment

### Prerequisites

- Active Google Cloud account with billing enabled
- Oracle Database@Google Cloud service access (available through the Oracle-Google Cloud partnership)
- Google Cloud CLI installed (for CLI-based approaches)
- Basic familiarity with cloud networking concepts
- Proper IAM permissions to create resources in Google Cloud

### Key Features of Oracle Autonomous Database on Google Cloud

- **Fully Managed Database**: Automated patching, backup, and recovery
- **High Availability**: Built-in redundancy and failover capabilities
- **Security**: Encryption at rest and in transit, network isolation
- **Scalability**: Flexible compute and storage options
- **Integration**: Native integration with Google Cloud services

### Table of Contents

1. [Google Cloud Console Authentication](#google-cloud-console-authentication)
2. [Setting Up a Google Cloud Project](#setting-up-a-google-cloud-project)
3. [Creating Oracle Database via Google Cloud Console](#creating-oracle-database-via-google-cloud-console)
4. [Google Cloud CLI Setup](#google-cloud-cli-setup)
5. [Infrastructure Setup with Google Cloud CLI](#infrastructure-setup-with-google-cloud-cli)
6. [Creating a Virtual Private Cloud (VPC)](#creating-a-virtual-private-cloud-vpc)
7. [Creating Subnets](#creating-subnets)
8. [Configuring Firewall Rules](#configuring-firewall-rules)
9. [Deploying Oracle Autonomous Database via Google Cloud CLI](#deploying-oracle-autonomous-database-via-google-cloud-cli)
10. [Accessing the Database](#accessing-the-database)
11. [Python and Java Connection Examples](#python-and-java-connection-examples)
12. [Monitoring and Troubleshooting](#monitoring-and-troubleshooting)

---

## Google Cloud Console Authentication

### Step 1: Navigate to Google Cloud Console

Open your browser and go to [https://console.cloud.google.com/](https://console.cloud.google.com/)

### Step 2: Sign In with Your Google Account

Sign in with your Google Cloud account credentials. If you don't have an account, create one at [https://cloud.google.com/](https://cloud.google.com/)

### Step 3: Select or Create a Project

In the top navigation bar, click on the project dropdown menu and:
- Select an existing project, or
- Click **NEW PROJECT** to create a new one

Enter a project name (e.g., "oracle-multicloud-demo") and click **CREATE**.

---

## Setting Up a Google Cloud Project

### Step 1: Enable Required APIs

In the Google Cloud Console, navigate to **APIs & Services** > **Enabled APIs and Services**.

Click **+ ENABLE APIS AND SERVICES** and search for the following APIs. Enable each one:

1. **Compute Engine API** - Required for virtual machines and networking
2. **Cloud Resource Manager API** - For managing project resources
3. **Oracle Cloud Infrastructure API** - For Oracle Database services
4. **Service Networking API** - For private service connections

### Step 2: Create a Service Account (Optional but Recommended)

Navigate to **APIs & Services** > **Credentials**.

Click **+ CREATE CREDENTIALS** > **Service Account**

- **Service Account Name**: Enter a descriptive name (e.g., "oracle-db-admin")
- **Service Account ID**: Auto-generated (you can customize)
- Click **CREATE AND CONTINUE**

Grant appropriate roles:
- **Basic** > **Editor** (for development/testing)
- **Or** select specific roles for production environments

Click **CONTINUE** and then **DONE**.

---

## Creating Oracle Database via Google Cloud Console

### Step 1: Search for Oracle Database Service

In the Google Cloud Console search bar, type "Oracle Database" and select the Oracle Database service from the results.

### Step 2: Create a New Oracle Autonomous Database

Click the **+ CREATE** button or **Create Instance** to begin the configuration wizard.

### Step 3: Configure Basic Database Settings

Fill in the following information:

- **Instance Name**: Enter a unique name for your database (e.g., "oracle-adb-instance")
- **Region**: Select the geographic region where you want to deploy
- **Availability Zone**: Choose an availability zone (for high availability)
- **Admin User Password**: Set a strong password for the ADMIN user
  - Minimum 12 characters
  - Must include uppercase, lowercase, numbers, and special characters

### Step 4: Select Database Workload Type

Choose the appropriate workload type for your use case:

- **Autonomous Transaction Processing (ATP)**: OLTP workloads, real-time transactions
- **Autonomous Data Warehouse (ADW)**: OLAP workloads, analytics, reporting
- **Autonomous JSON Database (AJD)**: Document-oriented, NoSQL-like access to JSON data
- **Oracle APEX**: Application development and hosting

### Step 5: Configure Database Version and Edition

- **Database Version**: Select the latest available version (e.g., 23ai, 21c)
- **Character Set**: UTF8 (recommended for most use cases)
- **Edition**: Choose between:
  - **Standard Edition** (lower cost, suitable for small to medium workloads)
  - **Enterprise Edition** (advanced features, higher performance)

### Step 6: Configure Networking

Choose your network access strategy:

#### Option A: Private Endpoint (Recommended)

- **Network Type**: Private
- **VPC Network**: Select an existing VPC or create a new one
- **Subnet**: Choose the target subnet
- **Private IP Range**: Auto-assigned or custom
- **Network Security Group**: Configure inbound/outbound rules

#### Option B: Public Endpoint

- **Network Type**: Public
- **Authorized Client CIDR Blocks**: Specify IP ranges that can access the database
  - Example: `203.0.113.0/24` (replace with your IP range)
  - For testing: `0.0.0.0/0` (allows all - NOT recommended for production)

### Step 7: Configure Backup and Recovery

- **Backup Retention Period**: Set to 7-30 days (default: 7 days)
- **Automatic Backups**: Enable (recommended)
- **Backup Storage Region**: Same as the primary region (or another for geo-redundancy)

### Step 8: Add Database Initializing Parameters (Optional)

Specify any custom initialization parameters for your database:

- Memory allocation
- Process limits
- Log settings
- Other database parameters

### Step 9: Review and Create

Review all configuration details on the **Review** screen:

- Verify instance name, region, and workload type
- Confirm network settings and security configurations
- Check estimated monthly cost

Click **CREATE** to deploy your Oracle Autonomous Database.

### Step 10: Monitor Deployment Progress

The deployment process typically takes 15-30 minutes. Monitor progress in the **Instances** view:

- **Provisioning**: Resources are being created
- **Available**: Database is ready for use
- **Failed**: Review error logs if deployment fails

---

## Google Cloud CLI Setup

### Installation

The Google Cloud CLI is a command-line tool available for Windows, macOS, and Linux.

**For macOS:**

Using Homebrew:
```bash
brew install google-cloud-cli
```

Or using curl:
```bash
curl https://sdk.cloud.google.com | bash
exec -l $SHELL
```

**For Linux (Ubuntu/Debian):**

```bash
sudo apt-get update
sudo apt-get install google-cloud-cli
```

**For Windows:**

Download the installer from [Google Cloud SDK](https://cloud.google.com/sdk/docs/install-sdk) and run it.

### Initialize the Google Cloud CLI

After installation, run:

```bash
gcloud init
```

This will:
1. Prompt you to log in with your Google account
2. Ask you to select a project
3. Set the default region and zone

### Authentication

To authenticate with your Google Cloud account:

```bash
gcloud auth login
```

To set your project:

```bash
gcloud config set project PROJECT_ID
```

Replace `PROJECT_ID` with your actual Google Cloud project ID.

---

## Infrastructure Setup with Google Cloud CLI

### Step 1: Set Default Region and Zone

```bash
gcloud config set compute/region us-central1
gcloud config set compute/zone us-central1-a
```

Replace `us-central1` with your preferred region.

### Step 2: Verify Your Project and Account

```bash
gcloud config list
gcloud auth list
```

---

## Creating a Virtual Private Cloud (VPC)

### Create a Custom VPC Network

```bash
gcloud compute networks create oracle-vpc \
  --subnet-mode=custom \
  --bgp-routing-mode=regional \
  --description="VPC for Oracle Autonomous Database"
```

### Verify VPC Creation

```bash
gcloud compute networks list
gcloud compute networks describe oracle-vpc
```

---

## Creating Subnets

### Create a Subnet in Your VPC

```bash
gcloud compute networks subnets create oracle-subnet \
  --network=oracle-vpc \
  --range=10.0.1.0/24 \
  --region=us-central1 \
  --description="Subnet for Oracle Database and Compute Engine instances"
```

### Create Additional Subnets (Optional)

For better security, create separate subnets:

```bash
# Database subnet
gcloud compute networks subnets create db-subnet \
  --network=oracle-vpc \
  --range=10.0.2.0/24 \
  --region=us-central1

# Application subnet
gcloud compute networks subnets create app-subnet \
  --network=oracle-vpc \
  --range=10.0.3.0/24 \
  --region=us-central1
```

### List Subnets

```bash
gcloud compute networks subnets list --network=oracle-vpc
```

---

## Configuring Firewall Rules

### Create Firewall Rules for Database Access

#### Rule 1: Allow Oracle Database Port (1521) from Application Subnet

```bash
gcloud compute firewall-rules create allow-oracle-db \
  --network=oracle-vpc \
  --allow=tcp:1521 \
  --source-ranges=10.0.3.0/24 \
  --target-tags=oracle-db \
  --description="Allow Oracle Database port 1521"
```

#### Rule 2: Allow SSH Access to Compute Engine Instances

```bash
gcloud compute firewall-rules create allow-ssh \
  --network=oracle-vpc \
  --allow=tcp:22 \
  --source-ranges=0.0.0.0/0 \
  --description="Allow SSH access"
```

#### Rule 3: Allow Internal Traffic Within VPC

```bash
gcloud compute firewall-rules create allow-internal \
  --network=oracle-vpc \
  --allow=tcp:0-65535,udp:0-65535,icmp \
  --source-ranges=10.0.0.0/16 \
  --description="Allow internal VPC traffic"
```

### List Firewall Rules

```bash
gcloud compute firewall-rules list --filter="network:oracle-vpc"
```

---

## Deploying Oracle Autonomous Database via Google Cloud CLI

### Create an Oracle Autonomous Database Instance

```bash
gcloud sql instances create oracle-adb-instance \
  --database-version=ORACLE_23AI \
  --tier=db-custom-4-16 \
  --region=us-central1 \
  --network=oracle-vpc \
  --no-assign-ip \
  --backup-start-time=02:00 \
  --enable-bin-log=false \
  --storage-auto-increase \
  --maintenance-window-day=SUN \
  --maintenance-window-hour=03 \
  --database-flags=character_set=AL32UTF8
```

**Note:** Replace parameters as needed:
- `--tier`: Machine type (db-custom-4-16 = 4 vCPUs, 16GB RAM)
- `--region`: Your preferred region
- Database version options: ORACLE_23AI, ORACLE_21C, ORACLE_19C

### Wait for Instance Creation

The instance creation typically takes 10-20 minutes. Monitor progress:

```bash
gcloud sql instances describe oracle-adb-instance
```

### Get Connection String

```bash
gcloud sql instances describe oracle-adb-instance \
  --format='value(ipAddresses[0].ipAddress)'
```

### Create a Database

```bash
gcloud sql databases create myappdb \
  --instance=oracle-adb-instance
```

### Create a Database User

```bash
gcloud sql users create appuser \
  --instance=oracle-adb-instance \
  --password=SecurePassword123!
```

---

## Accessing the Database

### Create a Compute Engine Instance for Access

```bash
gcloud compute instances create oracle-client-vm \
  --image-family=debian-11 \
  --image-project=debian-cloud \
  --region=us-central1 \
  --zone=us-central1-a \
  --subnet=oracle-subnet \
  --scopes=https://www.googleapis.com/auth/cloud-platform
```

### SSH into the Compute Engine Instance

```bash
gcloud compute ssh oracle-client-vm --zone=us-central1-a
```

### Install Oracle Client Tools

```bash
# Update system packages
sudo apt-get update

# Install necessary dependencies
sudo apt-get install -y build-essential libaio1 wget curl

# Download Oracle Client
wget https://download.oracle.com/otn_software/linux/instantclient/223000/instantclient-basic-linux.x64-23.3.0.23.09.zip
unzip instantclient-basic-linux.x64-23.3.0.23.09.zip

# Set LD_LIBRARY_PATH
export LD_LIBRARY_PATH=/path/to/instantclient:$LD_LIBRARY_PATH
```

### Connect Using sqlplus

```bash
sqlplus appuser@oracle-adb-instance:1521/myappdb
```

### Create a Port Forward for Local Access (Optional)

```bash
gcloud compute ssh oracle-client-vm \
  --zone=us-central1-a \
  --tunnel-through-iap \
  -- -L 1521:oracle-adb-instance:1521
```

Then connect locally:
```bash
sqlplus appuser@localhost:1521/myappdb
```

---

## Python and Java Connection Examples

### Python Connection

#### Install Required Packages

```bash
pip install cx_Oracle
```

#### Connect using Python

```python
import cx_Oracle

# Connection parameters
dsn = cx_Oracle.makedsn(
    host="oracle-adb-instance-ip",
    port=1521,
    service_name="myappdb"
)

# Establish connection
connection = cx_Oracle.connect(
    dsn=dsn,
    user="appuser",
    password="SecurePassword123!"
)

cursor = connection.cursor()

# Execute query
cursor.execute("SELECT * FROM user_tables")
for row in cursor.fetchall():
    print(row)

cursor.close()
connection.close()
```

#### Using sqlite3 Connection with Wallet (Secure)

```python
import cx_Oracle

# Create connection pool
cx_Oracle.init_oracle_client(lib_dir="/path/to/instantclient")

# Connection with wallet
connection = cx_Oracle.connect(
    "appuser",
    "password",
    dsn=cx_Oracle.makedsn(
        host="oracle-adb-instance-ip",
        port=1521,
        service_name="myappdb_high"
    )
)

cursor = connection.cursor()
cursor.execute("SELECT * FROM all_tables")
print(cursor.fetchall())
cursor.close()
connection.close()
```

### Java Connection

#### Add Maven Dependency

```xml
<dependency>
    <groupId>com.oracle.database.jdbc</groupId>
    <artifactId>ojdbc11</artifactId>
    <version>23.3.0.23.09</version>
</dependency>
```

#### Connect using Java

```java
import java.sql.*;

public class OracleConnection {
    public static void main(String[] args) {
        String url = "jdbc:oracle:thin:@oracle-adb-instance-ip:1521/myappdb";
        String user = "appuser";
        String password = "SecurePassword123!";
        
        try {
            // Register Oracle JDBC driver
            Class.forName("oracle.jdbc.driver.OracleDriver");
            
            // Create connection
            Connection conn = DriverManager.getConnection(url, user, password);
            
            // Execute query
            Statement stmt = conn.createStatement();
            ResultSet rs = stmt.executeQuery("SELECT * FROM user_tables");
            
            while (rs.next()) {
                System.out.println(rs.getString(1));
            }
            
            rs.close();
            stmt.close();
            conn.close();
            
        } catch (ClassNotFoundException e) {
            System.err.println("Oracle JDBC Driver not found");
            e.printStackTrace();
        } catch (SQLException e) {
            System.err.println("Connection failed");
            e.printStackTrace();
        }
    }
}
```

---

## Monitoring and Troubleshooting

### View Instance Status

```bash
gcloud sql instances describe oracle-adb-instance
```

### Check Instance Logs

```bash
gcloud sql operations list \
  --instance=oracle-adb-instance \
  --limit=10
```

### Monitor Instance Metrics

```bash
gcloud monitoring time-series list \
  --filter='resource.type="cloudsql_database" AND resource.labels.database_id="project:oracle-adb-instance"'
```

### Troubleshooting Common Issues

#### Issue 1: Cannot Connect to Database

**Solution:**
- Verify firewall rules allow traffic on port 1521
- Check VPC network configuration
- Ensure the database instance is in "Available" state
- Verify username and password are correct

#### Issue 2: Private Subnet Access

**Solution:**
- Ensure Cloud SQL Proxy is installed: `gcloud sql proxy -instances=project:region:instance-name &`
- Configure Private Service Connection in your VPC
- Use Private IP for internal connections

#### Issue 3: High Latency or Connection Timeouts

**Solution:**
- Check network latency: `ping oracle-adb-instance-ip`
- Verify bandwidth usage
- Consider moving Compute Engine instance to same region as database
- Check firewall rule priorities

### Enable Cloud SQL Proxy for Secure Remote Access

```bash
# Install Cloud SQL Proxy
curl -o cloud_sql_proxy https://dl.google.com/cloudsql/cloud_sql_proxy.linux.amd64
chmod +x cloud_sql_proxy

# Run Cloud SQL Proxy
./cloud_sql_proxy -instances=PROJECT_ID:REGION:INSTANCE_NAME &
```

---

## Best Practices

### Security

1. **Use Private Endpoints**: Never expose your database to the public internet
2. **Enable Encryption**: Use TLS for all connections
3. **Strong Passwords**: Use minimum 12 characters with mixed case, numbers, and symbols
4. **IAM Roles**: Grant principle of least privilege access
5. **Network Isolation**: Use VPCs and subnets for network segmentation

### Performance

1. **Monitor Metrics**: Regularly check CPU, memory, and disk usage
2. **Backup Strategy**: Automate daily backups with appropriate retention
3. **Connection Pooling**: Use connection pooling in applications
4. **Query Optimization**: Profile and optimize slow queries
5. **Scaling**: Plan for growth and scale resources accordingly

### Cost Optimization

1. **Right-sizing**: Start with appropriate instance size for your workload
2. **Use Reserved Instances**: For predictable, long-term workloads
3. **Turn Off Development Instances**: Stop instances when not in use
4. **Monitor Billing**: Set up budget alerts in Google Cloud Console
5. **Reserved IP Addresses**: Only allocate when necessary

---

## Useful Resources

- [Google Cloud Oracle Database Documentation](https://cloud.google.com/oracle)
- [Oracle Autonomous Database Documentation](https://docs.oracle.com/en/database/index.html)
- [Google Cloud SQL Documentation](https://cloud.google.com/sql/docs)
- [Google Cloud CLI Reference](https://cloud.google.com/cli/docs)
- [Oracle-Google Cloud Partnership](https://cloud.google.com/oracle)

---

## Next Steps

1. Set up monitoring and alerting
2. Configure automated backups
3. Implement connection pooling in your applications
4. Set up database performance tuning
5. Plan disaster recovery and high availability strategies
6. Integrate with other Google Cloud services (Cloud Run, App Engine, Dataflow)

