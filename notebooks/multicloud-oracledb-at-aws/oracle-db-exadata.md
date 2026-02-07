# Provision Oracle Exadata Database Service in Oracle Database@AWS

A comprehensive step-by-step guide to provisioning Oracle Exadata Database Service on Dedicated Infrastructure within AWS, enabling low-latency access to Oracle databases from AWS applications.

## Overview

Oracle Database@AWS is a strategic partnership between Oracle and Amazon Web Services that enables applications running in AWS Regions to use Oracle Exadata Database Service on Dedicated Infrastructure. This integration provides:

- **Low-latency access** from AWS to Oracle databases
- **Native AWS integration** with Amazon EC2, Kinesis, QuickSight, and other services
- **Oracle Database 23ai features** including AI Vector Search
- **Direct network connectivity** between VPC applications and ODB network

### Architecture

The architecture consists of:
- **AWS VPC** - Your application servers and AWS resources
- **ODB Network** - Private isolated network hosting OCI infrastructure
- **Exadata Infrastructure** - Database and storage servers with RDMA networking
- **Exadata VM Clusters** - Virtual machines hosting your Oracle databases
- **ODB Peering** - Secure connection between VPC and ODB network

## Prerequisites

1. **AWS Account**
   - Active AWS account with required permissions
   - AWS Management Console access
   
2. **Oracle Database@AWS Access**
   - Private offer from AWS Marketplace
   - Account activation by AWS/Oracle sales team
   - Estimated activation time: 1-2 business days

3. **Network Planning**
   - VPC CIDR range documented
   - Availability Zone selected for deployment
   - EC2 instance security groups identified

4. **Oracle License**
   - Bring Your Own License (BYOL) - recommended for existing customers
   - Or prepare for License Included option

5. **Credentials & Access**
   - SSH key pairs for VM cluster access
   - Administrator credentials for database
   - Backup storage configuration (S3 or OCI Object Storage)

## Task 1: Create the ODB Network

An ODB Network is a private, isolated network that hosts OCI infrastructure within an AWS Availability Zone, serving as the communication bridge between AWS and OCI.

### Step-by-Step Instructions

1. **Log in to AWS Management Console**
   - Open [AWS Management Console](https://console.aws.amazon.com/)
   - Sign in with your AWS credentials
   - Navigate to [Oracle Database@AWS Console](https://console.aws.amazon.com/odb/)

2. **Start ODB Network Creation**
   - In the left navigation, click **ODB networks**
   - Click **Create ODB network** button
   - Or directly from dashboard, under Step 1, click **Create ODB network**

3. **Enter Network Configuration**
   
   Complete the Create ODB Network form with:

   **Basic Information:**
   - **ODB Network Name**: Descriptive name (e.g., `prod-exadata-network`, `dev-odb-network`)
   - **Availability Zone**: Select target AZ (same as where you plan Exadata infrastructure)
   - **Description** (optional): Purpose and notes

   **Network CIDR Ranges:**
   - **Client Connection CIDR**: IP range for EC2 application servers
     - Example: `192.168.0.0/16`
     - Must be /24 or larger
     - Ensure no overlap with existing VPC ranges
   
   - **Backup Connection CIDR**: IP range for backup traffic to S3/OCI Object Storage
     - Example: `192.169.0.0/16`
     - Must be /24 or larger
     - Should differ from Client CIDR

   **Domain Configuration:**
   - **Domain Name Prefix** (optional): Custom domain prefix
     - Example: `mycompany`
     - Final FQDN will be: `mycompany.oraclevcn.com`
     - If not provided, uses auto-generated prefix

4. **Configure Advanced Options** (Optional)
   
   - **S3 Backup Access**: Enable if backing up to AWS S3
   - **Zero-ETL Integration**: Enable for Amazon Redshift analytics
   - **VPC Endpoint Configuration**: For AWS service connectivity
   - **Tags**: Add tags for cost tracking and resource management

5. **Review and Create**
   - Review all entered information
   - Verify CIDR ranges don't conflict with existing networks
   - Click **Create ODB network**
   - **Expected time**: 10-15 minutes
   - Status visible in dashboard transitions to "Available"

### Network Details Checklist

After successful creation, document the following:

```
ODB Network Details:
├── Network ID: odb-xxxxxxxx (auto-generated)
├── Network Name: prod-exadata-network
├── Region: us-east-1
├── Availability Zone: us-east-1a
├── Client Connection CIDR: 192.168.0.0/16
├── Backup Connection CIDR: 192.169.0.0/16
├── Domain Prefix: mycompany
├── Full Domain: mycompany.oraclevcn.com
├── Status: Available
└── Creation Time: YYYY-MM-DD HH:MM UTC
```

### Configure ODB Peering to VPC

After ODB network is created, set up peering to enable EC2 access:

1. **Navigate to ODB Peering**
   - From ODB Network details, click **Peering** tab
   - Note **Local Gateway Route Table ID**
   - Copy **ODB Network Client CIDR**

2. **Update EC2 VPC Route Tables**
   - Open EC2 console → VPC → Route Tables
   - Find your application's route table
   - Click **Edit routes**
   - Add route:
     - Destination: ODB Client CIDR (e.g., 192.168.0.0/16)
     - Target: Local Gateway Route Table (from peering info)
   - Save changes

3. **Verify Connectivity**
   ```bash
   # From EC2 instance in VPC
   ping <odb-network-hostname>.oraclevcn.com
   nslookup mycompany.oraclevcn.com
   ```

## Task 2: Create the Exadata Infrastructure

The Exadata Infrastructure is the underlying hardware architecture containing database servers, storage servers, and high-speed RDMA networking.

### Exadata Infrastructure Configuration

1. **Access Exadata Infrastructure Creation**
   - From ODB Dashboard, click **Exadata Infrastructures**
   - Click **Create Exadata Infrastructure**

2. **Step 1: Configure General Settings**
   
   - **Infrastructure Name**: Descriptive name
     - Example: `prod-exadata-01`, `exadata-primary`
     - Used for identification and resource tagging
   
   - **Availability Zone**: Select same AZ as ODB network
     - Must match ODB network AZ for optimal performance
   
   - **Display Name** (optional): Human-readable name for reporting
   
   - Click **Next** to proceed

3. **Step 2: Configure Exadata Infrastructure Shape**

   Select infrastructure size based on workload requirements:

   **Minimum Configuration (Pre-filled):**
   - Database Servers: 2
   - Storage Servers: 3
   - Total Storage: 240 TB (80 TB per storage server)

   **Scaling Options:**
   - **Database Servers**: 2-32 maximum
     - Add servers for higher CPU/memory needs
     - Each additional server adds compute capacity
   
   - **Storage Servers**: 3-64 maximum
     - Minimum 3 for data redundancy
     - Each additional server adds 80 TB storage
   - Example: 8 DB servers + 12 storage servers = 960 TB total

   **Sizing Guidelines:**
   
   | Workload | DB Servers | Storage | Use Case |
   |----------|-----------|---------|----------|
   | Dev/Test | 2 | 240 TB | Non-production testing |
   | Small Prod | 4 | 320 TB | Single small application |
   | Medium Prod | 8 | 640 TB | Multiple applications |
   | Large Prod | 16+ | 960+ TB | Enterprise deployments |

   > **Note**: Verify that your OCI tenancy limits allow the selected configuration

   - Click **Next** to proceed

4. **Step 3: Configure Maintenance and Tags**

   **Maintenance Schedule Configuration:**
   
   - **Patching Mode**:
     - **Oracle-managed** (default) - Oracle manages schedule and patching
     - **Customer-managed** - You control maintenance window timing
   
   - If Customer-managed selected:
     - **Month**: Select month within quarter
     - **Week**: Select week of month (1st, 2nd, 3rd, 4th, last)
     - **Day of Week**: Select preferred day (Mon-Sun)
     - **Starting Hour**: Time maintenance can begin
     - **Notification Days**: How far in advance to notify (0-30 days)
   
   - **Pre-Maintenance Timeout** (optional):
     - Time to wait before starting maintenance
     - Allows manual checks or script execution
     - Range: 0-120 minutes

   **Notification Contacts:**
   - **Email Addresses**: Up to 10 email addresses
     - Receives maintenance notifications
     - Example: `dba@company.com`, `ops-team@company.com`

   **Tagging** (optional but recommended):
   - **Environment**: `production`, `staging`, `development`
   - **Owner**: Team or department name
   - **Application**: Associated application name
   - **CostCenter**: Billing allocation code
   - **BackupStrategy**: Backup requirements
   - Custom tags as needed

   > **Note**: Maintenance settings can be updated from OCI Console later. You cannot modify infrastructure configuration after creation from AWS Console.

   - Click **Next** to proceed

5. **Step 4: Review and Create**

   **Review Section Contains:**
   - Infrastructure name and AZ
   - Database server count
   - Storage server count and capacity
   - Maintenance preferences
   - Tags

   **Before Creating:**
   - Verify all settings are correct
   - Confirm no configuration changes needed
   - Ensure sufficient quota in OCI tenancy

   **Options:**
   - Click **Previous** to go back and modify settings
   - Click **Cancel** to abandon creation
   - Click **Create Exadata Infrastructure** to proceed

6. **Creation Progress**

   - **Expected Duration**: 45-60 minutes
   - **Status Changes**:
     - Creating → Provisioning database/storage servers
     - Available → Infrastructure ready for VM clusters
   - **Monitor**: Dashboard shows real-time status
   - **Notifications**: Sent to configured email addresses

7. **Post-Creation - Exadata Infrastructure Summary**

   After successful creation, access the Summary tab to view:

   **Summary Information:**
   - **Configuration**: View all infrastructure settings
   - **Database Servers**: List of servers with specifications
   - **Exadata VM Clusters**: Clusters created on this infrastructure
   - **Autonomous VM Clusters**: Any autonomous VM clusters
   - **OCI Maintenance**: Link to OCI Console for maintenance updates
   - **Tags**: Associated tags for organization

   **Key Information to Save:**
   - Infrastructure ID
   - Database server count and configuration
   - Storage server count and total capacity
   - Maintenance window settings
   - OCI Console link for additional management

## Task 3: Create an Exadata VM Cluster

An Exadata VM Cluster is a set of virtual machines on the Exadata Infrastructure that will host your Oracle databases.

### Create Exadata VM Cluster

1. **Start VM Cluster Creation**
   - From ODB Dashboard, click **Exadata VM Clusters**
   - Click **Create VM Cluster**

2. **Step 1: Configure General Settings**

   - **VM Cluster Name**: Descriptive identifier
     - Example: `prod-vmcluster-01`, `exadata-cluster-primary`
     - Must be unique within Exadata Infrastructure

   - **Time Zone**: Database server timezone
     - Default: UTC
     - Examples: `America/New_York`, `Europe/London`, `Asia/Tokyo`
     - Used for database scheduling

   - **Time Zone for Reports** (optional): Separate timezone for reporting
     - If different from database timezone

   - **License Options**: Choose your licensing model
     - **Bring Your Own License (BYOL)**
       - Use existing Oracle Enterprise licenses
       - Best for existing Oracle customers
       - Reduces software costs
       - Requires Oracle license documentation
     
     - **License Included**
       - Oracle provides all licenses
       - Simpler procurement
       - Higher per-unit cost
       - No separate licensing required

   - Click **Next** to proceed

3. **Step 2: Configure Infrastructure Settings**

   - **Select Exadata Infrastructure**
     - Dropdown: Choose infrastructure created in Task 2
     - Displays available capacity
     - VM cluster will be deployed on this infrastructure

   - **Grid Infrastructure Version**: Select Oracle version
     - Options: 19c, 21c, 23ai (when available)
     - Determines supported Oracle Database versions
     - Example: Grid 23c required for Oracle Database 23ai
   
   - **Exadata Image Version**: Select OS/system software version
     - Latest version recommended
     - Determines OS version and available features
     - Includes OS updates and driver versions

   - **Database Servers**: Select which DB servers to use
     - Checkbox list of available servers
     - Example: Select servers 1, 2, 3 for this cluster
     - Multiple clusters can span same infrastructure

   **VM Configuration** - Allocate resources per VM:
   
   - **CPU Core Count** (OCPUs):
     - Minimum: 2 OCPUs per VM
     - Examples: 4, 8, 16, 20, 32 OCPUs
     - Allocates this many cores to each VM
   
   - **Memory per VM**:
     - Minimum: 30 GB per VM
     - Typical: 60 GB, 128 GB, 256 GB+
     - Each VM gets this much RAM
   
   - **Local Storage per VM**:
     - Minimum: 60 GB per VM
     - Typical: 100 GB, 200 GB, 500 GB+
     - Used for database files and logs

   **Storage Configuration** - Cluster-level storage allocation:
   
   - **Total Exadata Storage**: Enter in multiples of 1 TB
     - Minimum: 2 TB
     - Typical: 50 TB, 100 TB, 500 TB+
     - Shared among all VMs in cluster
   
   - **Enable Local Backups Storage** (optional):
     - Allows database backups to local Exadata storage
     - **Cannot be changed after creation**
     - Consider if planning local backup strategy
   
   - **Enable Sparse Snapshots** (optional):
     - Enables snapshot functionality
     - **Cannot be changed after creation**
     - For point-in-time recovery strategies

   - Click **Next** to proceed

4. **Step 3: Configure Connectivity**

   - **Select ODB Network**
     - Dropdown: Choose ODB network created in Task 1
     - Provides network isolation and peering

   - **Host Name Prefix**:
     - Prefix for VM hostnames
     - Example: `vmcluster01` → `vmcluster01-1.oraclevcn.com`, etc.
     - Used for DNS resolution

   - **SSH Key Pairs** (Important for access):
     - Click **Add SSH Key** to add public keys
     - Paste public key content (RSA format)
     - One key per button click
     - Multiple keys allow multiple users SSH access
     - Required for VM administration
     - Store private keys securely
     - Example:
       ```
       ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQC... user@hostname
       ```

   - **SCAN Listener Port** (optional):
     - Single Client Access Name listener port
     - Default: 1521 (standard Oracle port)
     - Custom range: 1024-8999
     - Used for database connections

   - Click **Next** to proceed or **Skip to Review and Create**

5. **Step 4: Configure Diagnostics and Tags**

   **Diagnostics** (optional):
   - **Enable OCI Diagnostic Collection**:
     - Oracle collects guest VM diagnostics
     - Helps identify and resolve issues quickly
     - Can be disabled anytime
     - Checkbox: Enable/Disable
   
   - **Subscribe to Events**:
     - Get notifications on resource state changes
     - Alerts for VM or cluster state changes
     - Requires notification configuration

   **Tags** (optional but recommended):
   - **Tag Namespace**: Select or create namespace
   - **Tag Key**: Descriptive key (e.g., `Environment`)
   - **Tag Value**: Tag value (e.g., `production`)
   - **Multiple Tags**: Click **Add another tag** for more
   
   Example tags:
   - `Environment: production`
   - `Application: ERP`
   - `Owner: DBA-Team`
   - `CostCenter: 12345`
   - `BackupPolicy: Daily`

   - Click **Next** to proceed

6. **Step 5: Review and Create**

   **Review All Settings:**
   - VM cluster name and timezone
   - Infrastructure and grid version selection
   - CPU, memory, and storage allocation
   - ODB network and SSH keys
   - Diagnostics and tags

   **Before Creating:**
   - Verify CPU/memory allocation adequate for workload
   - Confirm SSH keys are correct
   - Check storage allocation sufficient
   - Ensure tags correctly categorize resource

   **Options:**
   - Click **Previous** to modify settings
   - Click **Cancel** to abandon creation
   - Click **Create VM Cluster** to proceed

7. **Creation Progress and Monitoring**

   - **Expected Duration**: Up to 6 hours (depends on size)
   - **Status Progression**:
     - Creating (0-2 hours): Initial infrastructure setup
     - Available (2-6 hours): Configuring database servers
     - Ready (6 hours): VM cluster operational
   - **Monitor**: Dashboard shows real-time progress
   - **Notifications**: Email alerts on status changes

### Post-Creation VM Cluster Summary

After successful creation, access detailed information:

**Summary Tab Contains:**

- **Configuration**:
  - VM cluster name and ID
  - Grid Infrastructure version
  - Database server count
  - CPU/memory/storage per VM
  - Total cluster storage

- **Connectivity**:
  - Hostname prefix
  - SSH public keys
  - SCAN listener port
  - ODB network association

- **Monitoring**:
  - CPU utilization metrics
  - Memory utilization
  - Storage usage
  - Load average
  - Network metrics

- **OCI Resources**:
  - Direct link to OCI Console
  - Access for database creation
  - Infrastructure details

**Save Key Information:**
- VM Cluster ID
- Hostname pattern for DNS
- SCAN listener port
- Grid Infrastructure version
- Storage configuration details

## Task 4: Create Oracle Database

Oracle Database creation is managed from the OCI Console. With tight AWS-OCI integration, you can navigate directly from AWS Console.

### Create Your First Database

1. **Navigate to OCI Console**

   **From AWS Console:**
   - Open your VM Cluster details
   - Click **VM cluster name** or **Manage in OCI** button
   - You'll be redirected to OCI Console
   - Selected VM cluster will be pre-selected

   **Direct OCI Access:**
   - If you have OCI Console access, navigate directly
   - Go to **Databases** → **Exadata VM Clusters**
   - Select your VM cluster

2. **Start Database Creation**

   In the VM Cluster Details page:
   - Click **Databases** tab
   - Click **Create database** button
   - Database creation form opens

3. **Step 1: Basic Information**

   **Provide Database Name:**
   - **Database Name**: Unique identifier for database
     - Maximum: 8 characters
     - Only alphanumeric characters
     - Must begin with alphabetic character
     - Example: `PRODDB`, `APPSDB`, `FINDB`

   **Provide Unique Name** (optional):
   - Auto-generated if not specified
   - Format: `<db_name>_<3_char_unique>_<region>`
   - If you provide custom name:
     - Maximum: 30 characters
     - Alphanumeric or underscore (_) only
     - Begin with alphabetic character
     - Unique across VM cluster

   **Select Database Version**:
   - Available versions: 19c, 21c, 23ai (when available)
   - Example: Select Oracle Database 23ai for latest features
   - 23ai includes AI Vector Search for semantic search

   **Provide PDB Name** (optional):
   - Pluggable Database name
   - Maximum: 8 characters
   - Alphanumeric or underscore (_)
   - Begins with alphabetic character
   - Auto-generated if not specified
   - Example: `PDB01`, `APPPDB`
   - **Important**: Must be unique across VM cluster to avoid service name collisions

   **Database Home Source**:
   - **Select Existing Database Home**
     - Use previously created home
     - Faster deployment
   
   - **Create New Database Home**
     - Create dedicated home for this database
     - Specify: **Database Home Display Name**
     - Example: `PRODDB-HOME-1`

   **Additional Options**:
   - **Enable Unified Auditing**: Enable comprehensive audit logging
   - **Database Image** (optional): 
     - Oracle-published image (default)
     - Or custom database software image

4. **Step 2: Create Administrator Credentials**

   **SYS Password Creation** (critical):
   - **Password Requirements**:
     - 9-30 characters length
     - At least 2 UPPERCASE characters
     - At least 2 lowercase characters
     - At least 2 NUMERIC characters
     - At least 2 SPECIAL characters
     - Special characters allowed: `_`, `#`, `-`
     - Cannot contain username (SYS, SYSTEM, etc.)
     - Cannot contain "Oracle" forward or reversed

   - **Example Strong Password**:
     ```
     MyPro_D#01xABC
     (meets: 14 chars, 2+ upper/lower/numbers/special)
     ```

   - **Confirm Password**: Reenter password for verification

   **Optional Security Enhancement**:
   - Checkbox: **Use this password for TDE wallet**
     - TDE = Transparent Data Encryption
     - Uses same password for encryption wallet
     - Simplifies credential management

5. **Step 3: Configure Database Backups**

   **Enable Automatic Backup**:
   - Checkbox: **Enable Automatic Backups**
     - Recommended for production databases
     - Automatic daily backup schedule

   **Backup Destination**:
   - **Default**: Amazon S3
   - **Options**: S3 bucket or OCI Object Storage
   - Specify S3 bucket name if using S3
   - Ensure bucket has proper permissions

   **Backup Schedule**:
   - **Full Backup Schedule**:
     - Day of Week: Select day for weekly full backup
     - Example: Sunday (off-peak time)
     - Time Window: Select backup time window
     - Example: 02:00-04:00 UTC (midnight EST)
   
   - **Incremental Backup Schedule**:
     - Time Window: For daily incremental backups
     - Example: 23:00-01:00 UTC

   **Deletion Options After Termination**:
   - **Backup Retention**: Specify retention if DB is deleted
   - Options: Keep, delete after X days, or delete immediately
   - Example: Keep backups for 30 days after termination

6. **Advanced Options** (Optional but Recommended)

   Click **Show Advanced Options** to access additional settings:

   **Management Section**:
   
   - **Oracle SID Prefix** (optional):
     - System ID for Oracle instance naming
     - Maximum: 12 characters
     - Alphanumeric or underscore
     - Auto-generated from db_name if not specified
     - Must be unique in VM cluster
     - Example: `PROD`, `APP01`
   
   - **Character Set** (Database character encoding):
     - Default: **AL32UTF8** (recommended)
     - Supports all Unicode characters
     - Changing after creation is complex
     - Example alternatives: WE8ISO8859P1, UTF8
   
   - **National Character Set** (optional):
     - Default: AL16UTF16
     - For national language support

   **Encryption Section**:
   
   - **Key Management**:
     - **Oracle-Managed Keys** (default)
       - Oracle manages encryption keys
       - Simpler, no user overhead
       - Sufficient for most use cases
     
     - **Customer-Managed Keys**
       - You manage encryption keys
       - Full control over key lifecycle
       - Requires separate key management

   **Tags Section**:
   
   - **Tag Namespace**: Select or create namespace
   - **Tag Key/Value**: Add tags for organization
   - **Purpose**: Cost allocation, compliance, automation

   Example Tags:
   - `Environment: production`
   - `Application: ERP-System`
   - `DataClassification: Confidential`
   - `BackupSLA: Daily`
   - `Owner: Finance-Team`

7. **Review and Create**

   **Final Review**:
   - Verify database name and version
   - Check SYS password requirements met
   - Confirm backup configuration
   - Review advanced options
   - Check tags for accuracy

   **Validation**:
   - Database name: Valid format, unique
   - Password: Meets complexity requirements
   - Storage: Sufficient space in VM cluster
   - Network: Connectivity configured

   **Create Database**:
   - Click **Create Database** button
   - Provisioning begins
   - **Expected Duration**: 15-30 minutes
   - **Status**: Visible in database details

### Monitor Database Creation

1. **In OCI Console**:
   - Navigate to **Databases** tab
   - Select your database
   - Status shows provisioning progress
   - Transitions: Creating → Available → Ready

2. **CloudWatch Metrics** (in AWS Console):
   - CPU utilization increasing
   - Memory allocation
   - Network activity
   - Storage status

3. **Notifications**:
   - Email alerts on creation completion
   - Sent to configured contacts

## Connect to Your Database

Once the database is ready, establish connections from your applications.

### Obtain Connection Information

1. **From OCI Console**:
   - Open your database details
   - **Connection Information** tab shows:
     - Service names (HIGH, MEDIUM, LOW)
     - Connection strings
     - SCAN listener details

2. **Download Database Wallet**:
   - If using SSL/TLS connections
   - Contains certificates and connection info
   - Secure method for external connections

### Connection Methods

#### Option A: SQL*Plus (Command Line)

```bash
# Set TNS_ADMIN if using wallet
export TNS_ADMIN=/path/to/wallet

# Connect with service name
sqlplus SYS@<database>_MEDIUM

# At password prompt, enter SYS password
```

#### Option B: SQL Developer (GUI)

1. Create new connection:
   - Username: `SYS`
   - Password: Your administrator password
   - Hostname: SCAN listener hostname
   - Port: SCAN port (default 1521)
   - Service: `<database>_MEDIUM`
   - Connection Type: Standard or Cloud Wallet
   - Role: SYSDBA

2. Test Connection → Connect

#### Option C: Python (cx_Oracle)

```python
import cx_Oracle

# Connection parameters
dsn = cx_Oracle.makedsn(
    host='<scan-hostname>',
    port=1521,
    service_name='<database>_MEDIUM'
)

try:
    connection = cx_Oracle.connect(
        user='SYS',
        password='<password>',
        dsn=dsn,
        mode=cx_Oracle.SYSDBA
    )
    print("✓ Connected to Oracle Database")
    
    cursor = connection.cursor()
    cursor.execute('SELECT banner FROM v$version WHERE ROWNUM = 1')
    print(cursor.fetchone())
    
    cursor.close()
    connection.close()
except cx_Oracle.DatabaseError as e:
    print(f"✗ Connection failed: {e}")
```

#### Option D: JDBC (Java)

```java
// Connection string
String url = "jdbc:oracle:thin:@<scan-hostname>:1521/<database>_MEDIUM";
String user = "SYS";
String password = "<administrator_password>";

// JDBC connection
try {
    Class.forName("oracle.jdbc.OracleDriver");
    Connection connection = DriverManager.getConnection(url, user, password);
    System.out.println("✓ Connected to Oracle Database");
    
    Statement stmt = connection.createStatement();
    ResultSet rs = stmt.executeQuery("SELECT banner FROM v$version WHERE ROWNUM = 1");
    while (rs.next()) {
        System.out.println(rs.getString(1));
    }
    
    rs.close();
    stmt.close();
    connection.close();
} catch (SQLException e) {
    System.err.println("✗ Connection failed: " + e.getMessage());
}
```

## Data Migration

After database provisioning, migrate your data to the new Exadata Database.

### Migration Options

1. **Oracle Data Pump Export/Import**:
   ```bash
   # Export from source database
   expdp system/<password> full=Y directory=DPUMP_DIR \
     dumpfile=full_export_%U.dmp parallel=4
   
   # Import to Exadata database
   impdp system/<password> full=Y directory=DPUMP_DIR \
     dumpfile=full_export_%U.dmp parallel=4
   ```

2. **Oracle Zero Downtime Migration (ZDM)**:
   - Automated migration tool
   - Minimal/zero downtime
   - Automatic cutover
   - Recommended for production migrations

3. **Oracle GoldenGate**:
   - Real-time replication
   - Continuous synchronization
   - Planned or unplanned switchover
   - For high-availability requirements

## Monitoring and Management

### CloudWatch Monitoring (AWS Console)

1. **Access Metrics**:
   - CloudWatch → Metrics → AWS/ODB
   - Select VM cluster or database metrics

2. **Key Metrics**:
   - CPU Utilization
   - Memory Usage
   - Storage Space Used
   - Network I/O
   - Database Connections

3. **Create Alarms**:
   ```bash
   aws cloudwatch put-metric-alarm \
     --alarm-name exadata-cpu-high \
     --alarm-description "Alert when CPU > 80%" \
     --metric-name CPUUtilization \
     --namespace AWS/ODB \
     --statistic Average \
     --period 300 \
     --threshold 80 \
     --comparison-operator GreaterThanThreshold
   ```

### OCI Console Management

From OCI Console, you can:
- Monitor database performance
- View backup status
- Manage database parameters
- Configure additional settings
- Update infrastructure settings

## Troubleshooting

### Common Issues

**Issue**: Database creation fails with error
- **Solution**: Check VM cluster has sufficient storage and resources
- Verify administrator password meets complexity requirements
- Ensure database name is unique

**Issue**: Cannot connect to database
- **Solution**: Verify SCAN listener is running
- Check network connectivity between VPC and ODB network
- Confirm security group rules allow port 1521
- Test DNS resolution of SCAN hostname

**Issue**: Backup failures
- **Solution**: Verify S3 bucket permissions and connectivity
- Check backup storage allocation in VM cluster
- Review backup logs in OCI Console

## Best Practices

1. **Infrastructure Sizing**
   - Size for 80% peak load, not maximum
   - Plan growth over 3-5 years
   - Test with production-like data volumes

2. **High Availability**
   - Use Data Guard for standby protection
   - Configure automatic backups
   - Test restore procedures regularly

3. **Security**
   - Rotate SYS password regularly
   - Use strong administrator credentials
   - Enable Unified Auditing for compliance
   - Secure SSH keys and wallets

4. **Performance**
   - Monitor metrics consistently
   - Create appropriate indexes
   - Partition large tables
   - Use Oracle Database 23ai features (AI Vector Search, etc.)

5. **Backup Strategy**
   - Enable automatic backups
   - Store backups in multiple locations
   - Test recovery procedures
   - Document Recovery Time Objective (RTO)

## Next Steps

1. **Load Data**: Migrate or load your application data
2. **Configure Applications**: Update connection strings and test
3. **Optimize Database**: Create indexes, tune queries
4. **Enable Monitoring**: Set up CloudWatch alerts
5. **Document Procedures**: Backup, recovery, maintenance runbooks
6. **Train Team**: Ensure operations team knows how to manage Exadata

## Related Resources

- [Oracle Exadata Database Service Overview](https://docs.oracle.com/en/engineered-systems/exadata-cloud-service/ecscm/exadata-cloud-infrastructure-overview.html)
- [Oracle Exadata Video Playlist](https://www.youtube.com/playlist?list=PLdtXkK5KBY55lKBR3SS3YrbfgxcgdC6ZT)
- [Oracle LiveLabs Exadata Workshop](https://apexapps.oracle.com/pls/apex/f?p=133:180:17374221011687::::wid:3311)
- [Oracle Zero Downtime Migration](https://www.oracle.com/database/zero-downtime-migration/)
- [AWS ODB Documentation](https://docs.aws.amazon.com/odb/)
- [OCI Exadata Documentation](https://docs.oracle.com/en/engineered-systems/exadata-cloud-service/)

## Summary

Provisioning Oracle Exadata Database Service on AWS involves four simple but comprehensive tasks:

1. ✓ **Create ODB Network** - Private isolated network infrastructure (10-15 min)
2. ✓ **Create Exadata Infrastructure** - Database and storage servers (45-60 min)
3. ✓ **Create Exadata VM Cluster** - Virtual machines for databases (up to 6 hours)
4. ✓ **Create Oracle Database** - Actual database instance (15-30 min)

**Total Provisioning Time**: Up to 7-8 hours from start to ready-for-use database

Once provisioned, you have a production-grade Oracle Exadata infrastructure on AWS with low-latency access from your EC2 applications, enabling use of Oracle Database 23ai features including AI Vector Search for semantic similarity searches.

For semantic similarity search implementation, refer to the [Oracle RAG Agents notebook](../rag-aiagent-chatbot/RAGChatbotwithAgentDevelopmentKit.ipynb) for code examples and best practices.
