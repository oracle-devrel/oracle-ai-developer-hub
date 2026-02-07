# Creating Oracle Autonomous Database on AWS

A comprehensive guide to provisioning Oracle Autonomous Database on Dedicated Exadata Infrastructure within AWS using Oracle Database@AWS.

## Overview

Oracle Database@AWS is a managed service that brings Oracle Exadata workloads to AWS, providing two key offerings:

1. **Oracle Exadata Database Service on Dedicated Infrastructure** - Full control over Oracle Enterprise Edition with RAC capabilities
2. **Oracle Autonomous Database on Dedicated Exadata Infrastructure** - Fully managed database with AI/ML automation

This guide focuses on setting up Oracle Autonomous Database on Dedicated Exadata Infrastructure.

## Key Benefits

- **Simplified Migration** - Migrate Oracle Exadata workloads with minimal changes
- **Single Invoice** - Unified billing through AWS Marketplace
- **AWS Integration** - Use AWS Console, CLI, and APIs for management
- **High Availability** - Exadata infrastructure with zero-ETL and S3 backups
- **Enterprise Features** - Full Oracle Enterprise Edition capabilities
- **Regional Flexibility** - Available in U.S. East (N. Virginia) and U.S. West (Oregon), expanding to 20+ regions globally

## Prerequisites

1. **AWS Account** - Active AWS account with appropriate permissions
2. **AWS Marketplace Access** - Access to Oracle Database@AWS offering
3. **Oracle License** - Bring Your Own License (BYOL) or license included options
4. **VPC Setup** - Existing VPC for EC2 application servers
5. **Permissions** - IAM permissions to manage ODB resources
6. **Sales Team Contact** - Coordinate with AWS/Oracle sales for account activation

## Step 1: Request Access to Oracle Database@AWS

### Via AWS Marketplace

1. Sign in to [AWS Management Console](https://console.aws.amazon.com/)
2. Navigate to AWS Marketplace
3. Search for **Oracle Database@AWS**
4. Click on the offering
5. Select **Request a Private Offer**

### Via AWS Console

1. Go to [Oracle Database@AWS Console](https://console.aws.amazon.com/odb/home)
2. Click **Get Started**
3. Request a private offer through AWS Marketplace

### Sales Team Engagement

- Your AWS and Oracle sales teams will receive your request
- They will contact you to understand your workload requirements
- Discuss licensing options (BYOL vs. License Included)
- Activate your account for access
- Estimated timeframe: 1-2 business days

## Step 2: Create an ODB Network

An ODB Network is a private, isolated network that hosts OCI infrastructure on AWS, serving as the communication bridge between AWS and OCI.

### Via AWS Console

1. **Access ODB Dashboard**
   - Open [Oracle Database@AWS Console](https://console.aws.amazon.com/odb/home)
   - Select your region (US East N. Virginia or US West Oregon)

2. **Create ODB Network**
   - Click **Create ODB network**
   - Provide the following details:

   **Basic Configuration:**
   - **Network Name**: e.g., `prod-autonomous-network`
   - **Availability Zone**: Select target AZ (e.g., us-east-1a)
   
   **Network CIDR Ranges:**
   - **Client Connection CIDR**: e.g., `192.168.0.0/16` (for EC2 applications)
   - **Backup Connection CIDR**: e.g., `192.169.0.0/16` (for S3 backups)
   - Note: Each range must be a /24 or larger

   **Domain Configuration:**
   - **Domain Name Prefix**: e.g., `mycompany` (optional)
   - Final FQDN: `mycompany.oraclevcn.com`

3. **Configure Advanced Options** (Optional)
   - **S3 Backup Access**: Enable automated backups to Amazon S3
   - **Zero-ETL Integration**: Enable for Amazon Redshift analytics
   - **VPC Endpoint Configuration**: For secure AWS service connectivity

4. **Review and Create**
   - Review all settings
   - Click **Create**
   - Creation typically takes 10-15 minutes
   - Status visible in dashboard

### Network Details Reference

After creation, note these details for later configuration:

```
ODB Network Information:
├── Network ID: odb-xxxxxxx
├── Network Name: prod-autonomous-network
├── Availability Zone: us-east-1a
├── Client CIDR: 192.168.0.0/16
├── Backup CIDR: 192.169.0.0/16
├── Domain: mycompany.oraclevcn.com
└── Status: Available
```

## Step 3: Configure VPC Route Tables (For EC2 Access)

Update your EC2 VPC route tables to enable connectivity to the ODB network.

### Update EC2 VPC Route Tables

1. **Get ODB Network Peering Information**
   - From ODB Dashboard, go to **ODB Peering**
   - Note the **Local Gateway Route Table ID**
   - Copy the **ODB Network CIDR** (client connection range)

2. **Access VPC Console**
   - Open EC2 → VPC → Route Tables
   - Find your application's VPC route table

3. **Add Route to ODB Network**
   - Click **Edit routes**
   - Click **Add route**
   - **Destination**: Enter ODB Network Client CIDR (e.g., 192.168.0.0/16)
   - **Target**: Select **Local Gateway Route Table** (from ODB Peering)
   - Click **Save routes**

4. **Verify Connectivity**
   ```bash
   # From EC2 instance in the VPC
   ping <odb-network-dns-name>
   
   # Test DNS resolution
   nslookup <hostname>.oraclevcn.com
   ```

## Step 4: Create Exadata Infrastructure

The Exadata infrastructure is the underlying hardware architecture (database servers, storage servers, networking) that runs your autonomous databases.

### Via AWS Console

1. **Create Exadata Infrastructure**
   - From ODB Dashboard, click **Create Exadata infrastructure**
   - Provide the following details:

   **Basic Information:**
   - **Infrastructure Name**: e.g., `prod-exadata-01`
   - **Availability Zone**: Use same AZ as ODB Network
   - **Display Name**: Human-readable name for reference

2. **Select Exadata System Model**
   - **System Model**: Select `Exadata.X11M` (latest generation)
   - Other options may be available based on your region

3. **Configure Database Servers**
   - **Minimum**: 2 database servers
   - **Maximum**: Up to 32 database servers
   - Choose based on your workload CPU/memory needs
   - Default configuration: 2 servers

4. **Configure Storage Servers**
   - **Minimum**: 3 storage servers
   - **Maximum**: Up to 64 storage servers
   - **Storage Capacity per Server**: 80 TB
   - Default configuration: 3 servers (240 TB total)

5. **Maintenance Preferences**
   - **Patching Mode**: 
     - *Rolling* (default) - minimal downtime
     - *Non-rolling* - single maintenance window
   - **Maintenance Window**: Schedule preferred time
   - **OCI Notification Contacts**: Email addresses for maintenance notifications
   - **Timezone**: Set appropriate timezone

6. **Review and Create**
   - Review all infrastructure settings
   - Click **Create Exadata infrastructure**
   - Creation typically takes 45-60 minutes
   - Status shown in dashboard

### Exadata Infrastructure Sizing Guide

| Workload Size | DB Servers | Storage Servers | Total Storage | Use Case |
|---------------|-----------|-----------------|---------------|----------|
| Small | 2 | 3 | 240 TB | Dev/Test, Small Production |
| Medium | 4 | 6 | 480 TB | Mid-size Production |
| Large | 8 | 12 | 960 TB | Enterprise Production |
| Extra Large | 16+ | 32+ | 2.5+ PB | Large Enterprise |

**Note**: You cannot modify infrastructure after creation via AWS Console. For changes, use OCI Console.

## Step 5: Create Autonomous VM Cluster

An Autonomous VM Cluster is a fully managed set of virtual machines that automate key database management tasks using AI/ML.

### Via AWS Console

1. **Create Autonomous VM Cluster**
   - From ODB Dashboard, click **Create Exadata VM cluster**
   - Select **Autonomous VM Cluster** as the type

2. **Basic Configuration**
   - **VM Cluster Name**: e.g., `prod-autonomous-cluster-01`
   - **Timezone**: Select database timezone (e.g., America/New_York)
   - **Time Zone for Reports**: Same or different timezone for reporting

3. **Licensing Options**
   - **Bring Your Own License (BYOL)**
     - Use existing Oracle licenses
     - Best for existing Oracle customers
     - Requires Oracle license count documentation
   - **License Included**
     - Oracle provides licenses
     - Simpler procurement
     - Higher per-unit cost

4. **Infrastructure & Version Selection**
   - **Exadata Infrastructure**: Select previously created infrastructure
   - **Grid Infrastructure Version**: Select latest available (e.g., 21c)
   - **Exadata Image Version**: Use recommended latest version
   
5. **Database Server Configuration**
   - **CPU Cores per Server**: Choose based on workload
     - Small: 16-20 cores
     - Medium: 28-32 cores
     - Large: 40+ cores
   - **Memory per Server**: Typically 2-4 GB per core
   - **Local Storage**: SSD storage for database files and logs
   - Click **Accept defaults** for standard sizing or **Customize**

6. **Connectivity & Access**
   - **Select ODB Network**: Choose your created ODB network
   - **VM Cluster Prefix**: e.g., `autonomous-prod`
     - Used for DNS naming
     - Format: `<prefix>.<domain>` (e.g., autonomous-prod.mycompany.oraclevcn.com)
   
   **Network Access Configuration:**
   - **SCAN Listener Port**: Default `1521` or custom port (1024-8999)
   - **SSH Key Pairs**: Paste public key(s) for SSH access
     - Click **Add SSH Key**
     - Paste public key content
     - Add multiple keys if needed

7. **Diagnostics & Monitoring** (Optional)
   - **Enable Enterprise Manager**: For advanced monitoring
   - **Enable Diagnostics**: CloudWatch metrics collection
   - **CloudWatch Namespace**: `AWS/ODB` (default)

8. **Tags** (Optional but recommended)
   - **Environment**: e.g., `production`
   - **Owner**: Team or department name
   - **Application**: Application name
   - **CostCenter**: For billing allocation

9. **Review and Create**
   - Review all VM cluster settings
   - Verify licensing selection
   - Confirm SSH key configuration
   - Click **Create Autonomous VM cluster**
   - **Creation time**: Up to 6 hours (depending on cluster size)
   - Monitor progress in dashboard

### VM Cluster Creation Status

```
Status Progression:
1. Creating (0-2 hours) - Infrastructure initialization
2. Available (2-6 hours) - Configuring database servers
3. Ready (6 hours) - Autonomous VM cluster operational
```

## Step 6: Create Oracle Autonomous Database

Once the Autonomous VM Cluster is ready, create autonomous databases within it.

### Via OCI Console

**Note**: Autonomous databases are created in the OCI Console, not AWS Console.

1. **Access OCI Console**
   - From AWS ODB Dashboard, click **Manage in OCI**
   - You'll be redirected to OCI Console
   - Select your OCI compartment for the VM cluster

2. **Create Autonomous Database**
   - Go to **Oracle Database** → **Autonomous Database**
   - Click **Create Autonomous Database**
   - Select **Dedicated Infrastructure**

3. **Provide Database Information**
   - **Display Name**: e.g., `prod-autonomous-db`
   - **Database Name**: e.g., `PRODADB` (alphanumeric, max 14 characters)
   - **Workload Type**: Select **Autonomous Database on Dedicated Infrastructure**

4. **Select VM Cluster**
   - **Autonomous VM Cluster**: Select your created cluster
   - **Container Database**: Will auto-create or use existing

5. **Database Configuration**
   - **Administrator Password**: Create strong password
     - Minimum 12 characters
     - Mix of uppercase, lowercase, numbers, special characters
   - **Database Version**: Oracle 19c or 23ai
   - **Character Set**: AL32UTF8 (recommended) or your choice

6. **Advanced Options**
   - **Auto Scaling**: Enable CPU/storage auto-scaling
   - **Backup Retention**: 7-60 days (default 30)
   - **Encryption**: Use Oracle managed keys or your key
   - **Backup Location**: 
     - S3 bucket (for AWS backups)
     - OCI Object Storage (default)

7. **Backup Configuration**
   - **Enable Backup**: Strongly recommended
   - **Backup Destination**: S3 bucket (AWS) or Object Storage (OCI)
   - **Automated Backups**: Daily backups configured automatically

8. **Create Database**
   - Review all settings
   - Click **Create Autonomous Database**
   - **Provisioning time**: 15-30 minutes
   - Status visible in OCI Console

### Database Sizing Recommendations

| Workload | CPU Cores | Memory | Storage | PDB Users |
|----------|-----------|--------|---------|-----------|
| Development | 1-2 | 4-8 GB | 20-50 GB | 1-5 |
| Testing | 2-4 | 8-16 GB | 50-100 GB | 5-10 |
| Production | 4+ | 16+ GB | 100+ GB | 10+ |
| Enterprise | 8+ | 32+ GB | 500+ GB | 50+ |

## Step 7: Connect to Autonomous Database

After the database is created and ready, establish connections from your applications.

### Get Connection Details

1. **From OCI Console**
   - Navigate to **Autonomous Database** → Your database
   - Click **Database Connection**
   - Download **Wallet** (for secure connections)
   - Note the **Connection String** for your service

2. **Available Services**
   - `<database>_high` - For batch operations
   - `<database>_medium` - For general use (recommended)
   - `<database>_low` - For lightweight connections

### Connection Methods

#### Option A: Using SQL Developer

1. Download and install [Oracle SQL Developer](https://www.oracle.com/database/sqldeveloper/)
2. Create new database connection:
   - Connection Name: `prod-autonomous-db`
   - Username: `ADMIN`
   - Password: Administrator password
   - Connection Type: **Cloud Wallet**
   - Configuration File: Download wallet from OCI Console
   - Service: `<database>_medium`
3. Test Connection → Connect

#### Option B: Using SQL*Plus

```bash
# Extract wallet and configure sqlnet.ora
unzip Wallet_<dbname>.zip

# Connect
sqlplus admin@<database>_medium@<wallet_path>/sqlnet.ora

# Enter password
```

#### Option C: Using Python (cx_Oracle)

```python
import cx_Oracle
import os

# Download wallet from OCI Console
wallet_location = '/path/to/wallet'
os.environ['TNS_ADMIN'] = wallet_location

try:
    connection = cx_Oracle.connect(
        user='admin',
        password='<administrator_password>',
        dsn='<database>_medium',
        configdir=wallet_location
    )
    print("✓ Successfully connected to Autonomous Database")
    
    cursor = connection.cursor()
    cursor.execute('SELECT banner FROM v$version WHERE ROWNUM = 1')
    print(cursor.fetchone())
    
    cursor.close()
    connection.close()
except cx_Oracle.DatabaseError as e:
    print(f"✗ Connection failed: {e}")
```

#### Option D: Using JDBC (Java)

```java
import java.sql.Connection;
import java.sql.DriverManager;

public class AutonomousDBConnection {
    public static void main(String[] args) {
        String url = "jdbc:oracle:thin:@<database>_medium?TNS_ADMIN=/path/to/wallet";
        String username = "admin";
        String password = "<administrator_password>";
        
        try {
            Class.forName("oracle.jdbc.OracleDriver");
            Connection connection = DriverManager.getConnection(url, username, password);
            System.out.println("✓ Connected to Autonomous Database");
            connection.close();
        } catch (Exception e) {
            System.err.println("✗ Connection failed: " + e.getMessage());
        }
    }
}
```

## Step 8: Configure Backups and Recovery

Autonomous databases have automated backup strategies configured.

### Backup Configuration

1. **In OCI Console**
   - Navigate to your Autonomous Database
   - Go to **Backup** tab
   - Review automatic backup schedule
   - Create manual backups before major changes
   - Set retention period (7-60 days)

2. **Backup Locations**
   - **OCI Object Storage** - Default backup location
   - **Amazon S3** - For AWS-based backups
     - Enable in backup settings
     - Provide S3 bucket name and IAM role

3. **Point-in-Time Recovery (PITR)**
   - Enables recovery to any point within retention window
   - Automatically enabled
   - No additional configuration needed

### Configure S3 Backups

1. **Create S3 Bucket**
   ```bash
   aws s3 mb s3://oracle-autonomous-backups-<account-id>
   ```

2. **Create IAM Role for OCI**
   - Trust relationship to OCI
   - S3 bucket permissions
   - Document role ARN

3. **Enable S3 Backups**
   - From Autonomous Database → Backup
   - Click **Configure S3 Backups**
   - Enter S3 bucket name
   - Provide IAM role ARN
   - Test connection

## Step 9: Monitoring and Management

### CloudWatch Monitoring

Monitor your Autonomous Database using CloudWatch metrics.

1. **Available Metrics**
   - Go to **CloudWatch** → **Metrics** → **AWS/ODB**
   - Available metric namespaces:
     - VM Cluster metrics
     - Container Database metrics
     - Pluggable Database metrics

2. **Key Metrics to Monitor**
   - CPU Utilization
   - Database Connections
   - Storage Usage
   - Network I/O
   - Read/Write Latency
   - Backup Status

3. **Create Alarms**
   ```bash
   aws cloudwatch put-metric-alarm \
     --alarm-name autonomous-db-cpu-high \
     --alarm-description "Alert when CPU > 80%" \
     --metric-name CPUUtilization \
     --namespace AWS/ODB \
     --statistic Average \
     --period 300 \
     --threshold 80 \
     --comparison-operator GreaterThanThreshold
   ```

### CloudTrail Logging

All AWS API calls are logged in CloudTrail for audit purposes.

1. **Enable CloudTrail**
   - Already enabled by default for Oracle Database@AWS
   - Logs available in CloudTrail console

2. **Query Logs**
   - View API calls made to Oracle Database@AWS
   - Filter by resource, event type, or time range
   - Export logs to S3 for analysis

### EventBridge Integration

Configure automated responses to database lifecycle events.

1. **Create Event Rules**
   ```bash
   aws events put-rule \
     --name autonomous-db-backup-complete \
     --event-pattern '{"source":["aws.odb"],"detail-type":["Backup Complete"]}'
   ```

2. **Configure Targets**
   - SNS for notifications
   - Lambda for automated actions
   - SQS for event queuing

## Step 10: Security Configuration

### IAM Access Control

1. **Create IAM Policies**
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Action": [
           "odb:DescribeAutonomousDatabase",
           "odb:DescribeExadataInfrastructure",
           "odb:CreateDatabase"
         ],
         "Resource": "arn:aws:odb:*:*:*"
       }
     ]
   }
   ```

2. **Assign to IAM Users/Roles**
   - Grant principle of least privilege
   - Separate read-only vs. admin access
   - Use roles for EC2 instances

### Network Security

1. **VPC Configuration**
   - ODB network is isolated private network
   - EC2 access via peering only
   - Configure security groups at VPC level

2. **SSL/TLS Encryption**
   - All connections encrypted by default
   - Use wallet for certificate-based authentication
   - Monitor certificate expiration

### Encryption Options

1. **Encryption at Rest**
   - AWS managed keys (default)
   - Customer managed keys (KMS)
   - Oracle managed keys (in OCI)

2. **Encryption in Transit**
   - SSL/TLS for all network connections
   - Wallet-based authentication
   - No plaintext credentials in transit

## Troubleshooting

### Common Issues and Solutions

#### Connection Failures

**Issue**: "Cannot connect to database"
- Verify ODB network is in Available state
- Check VPC route tables include ODB network CIDR
- Confirm security groups allow traffic on port 1521
- Verify DNS resolution: `nslookup <hostname>.oraclevcn.com`

**Issue**: "TNS listener does not know of service"
- Verify service name is correct (`<database>_medium`, etc.)
- Confirm database is in Ready state
- Check wallet is current and not expired

#### Backup Issues

**Issue**: "Backup failed to S3"
- Verify S3 bucket exists and is accessible
- Check IAM role permissions for S3 bucket
- Confirm ODB network has S3 endpoint connectivity
- Review backup logs in CloudWatch

#### Performance Issues

**Issue**: "Slow query performance"
- Check CloudWatch CPU and I/O metrics
- Review database session count
- Consider auto-scaling enabled option
- Analyze execution plans in OCI Console
- Contact Oracle support for performance tuning

### Support Resources

- **AWS Support**: Through AWS Support Console
- **Oracle Support**: Through OCI Support channels
- **AWS Partners**: Oracle Competency Partners for implementation assistance
- **Documentation**: 
  - [AWS ODB User Guide](https://docs.aws.amazon.com/odb/)
  - [OCI Documentation](https://docs.oracle.com/iaas/database-at-aws/)

## Cost Estimation

Oracle Database@AWS pricing includes:

1. **Infrastructure Costs**
   - Exadata infrastructure (per month)
   - Database servers (CPU-based)
   - Storage servers (capacity-based)

2. **Software Costs**
   - Oracle database licenses (if License Included)
   - Support and updates

3. **Additional AWS Costs**
   - S3 storage for backups
   - Data transfer (cross-region)
   - CloudWatch monitoring

**Estimate**: Use [Oracle Pricing Calculator](https://www.oracle.com/cloud/aws/pricing) for your specific configuration.

## Best Practices

1. **Infrastructure Planning**
   - Size infrastructure for 80% peak load
   - Plan for growth over next 3-5 years
   - Account for dev/test environments

2. **Backup Strategy**
   - Maintain 30-day retention minimum
   - Test restore procedures regularly
   - Use S3 for geographic redundancy

3. **Monitoring**
   - Enable CloudWatch metrics
   - Configure alarms for key thresholds
   - Review logs regularly

4. **Security**
   - Rotate passwords regularly
   - Keep wallet files secure
   - Use IAM roles for application access
   - Enable audit logging

5. **Performance**
   - Use appropriate service names for workload
   - Enable auto-scaling for variable workloads
   - Monitor and tune slow queries
   - Use partitioning for large tables

6. **Migration**
   - Plan migration carefully
   - Test with production-like datasets
   - Use Oracle Data Pump for data migration
   - Validate application compatibility

## Next Steps

After creating your Autonomous Database:

1. **Load Data**
   - Migrate existing data using Oracle Data Pump
   - Or load sample datasets for testing

2. **Configure Applications**
   - Update connection strings
   - Distribute wallet files securely
   - Test application connectivity

3. **Optimize Performance**
   - Create indexes for frequently queried columns
   - Partition large tables
   - Monitor and tune slow queries

4. **Implement Backups**
   - Configure S3 backup destination
   - Test restore procedures
   - Document recovery runbooks

5. **Enable Monitoring**
   - Set up CloudWatch alarms
   - Configure EventBridge notifications
   - Review AWS CloudTrail logs regularly

## Additional Resources

- **AWS Documentation**
  - [Oracle Database@AWS User Guide](https://docs.aws.amazon.com/odb/)
  - [Onboarding Guide](https://docs.aws.amazon.com/odb/latest/UserGuide/setting-up.html)
  - [How It Works](https://docs.aws.amazon.com/odb/latest/UserGuide/how-it-works.html)

- **Oracle Documentation**
  - [Database@AWS on OCI](https://docs.oracle.com/en/cloud/paas/autonomous-database/adbda/)
  - [Autonomous Database Dedicated](https://docs.oracle.com/en/cloud/paas/autonomous-database/)
  - [Provisioning Guide](https://docs.oracle.com/en/learn/exadb-provisioning-aws/)

- **Support Channels**
  - AWS Support through AWS Console
  - OCI Support for Oracle-specific issues
  - AWS Marketplace for billing questions
  - Partner Network for implementation help

## Summary

Creating Oracle Autonomous Database on AWS involves:

1. ✓ Requesting access and account activation
2. ✓ Creating an ODB network for private infrastructure
3. ✓ Configuring VPC routes for EC2 connectivity
4. ✓ Provisioning Exadata infrastructure (45-60 minutes)
5. ✓ Creating Autonomous VM cluster (up to 6 hours)
6. ✓ Deploying autonomous databases in OCI Console
7. ✓ Establishing secure connections from applications
8. ✓ Configuring backups and monitoring
9. ✓ Implementing security best practices
10. ✓ Monitoring and optimizing performance

For semantic similarity search using embeddings with your autonomous database, refer to the [Oracle RAG Agents notebook](../rag-aiagent-chatbot/RAGChatbotwithAgentDevelopmentKit.ipynb).
