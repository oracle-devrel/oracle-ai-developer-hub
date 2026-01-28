# Unlocking Oracle AI Database API for MongoDB with Google Colab
 
## Introduction

Oracle Database API for MongoDB makes it possible to connect to Oracle Autonomous AI Database using MongoDB language drivers and tools. This enables developers familiar with MongoDB to leverage Oracle's converged database capabilities—including JSON storage, SQL querying, and AI features—without changing their application architecture.

Oracle Database API for MongoDB allows you to use standard MongoDB drivers and tools while accessing Oracle Autonomous AI Database. This lets you manage multiple data types (relational, JSON, graph, vector) within a single database and query them seamlessly with SQL.

Get ready to experience the power of Oracle AI Database API for MongoDB! 
 
Perfect for developers and data professionals looking to leverage the flexibility of MongoDB API with the power of Oracle's Autonomous Database. 
 
💻 #MongoDB API #Oracle #AutonomousDatabase #DataScience #GoogleColab #Notebook

![Enable ACL](images/developer.jpeg)

Estimated Time: 20 mins.

### Objectives

🚀 In this lab, you'll learn how to:

* ✅ Enable MongoDB API access
* ✅ Connect using MongoDB drivers (Python/Node.js)
* ✅ Execute MongoDB queries against Oracle data
* ✅ Query the same data using SQL and MongoDB API interchangeably
* ✅ Run MongoDB APIs using Google Colab Notebooks. 

### Prerequisites

This lab assumes you have:
* Oracle Cloud account with privileges to create and manage Oracle Autonomous AI Database
* Oracle Autonomous AI Database instance 26ai deployed 
* MongoDB driver installed (Python, Node.js, SQL Worksheet or Google Colab Notebook)
  
Download and Run [Google Colab Notebook](mongodb_create_customers.ipynb). Follow the instructions from Task 1 & Task 6
 
## Task 1: Enable MongoDB API on Your Database

1. Login to [Cloud.oracle.com](https://cloud.oracle.com) and navigate to **Oracle AI Database** → **Autonomous AI Database**. Ensure you've selected the correct region and compartment.

2. Click your database instance to open its details page.

3. Under **Network** settings, change from **Allow secure access from everywhere** to **Allow secure access from specified IPs and VCNs**.

    ![Enable ACL](images/enable-acl1.png)

4. Add your machine's public IP address to the access control list.

    ![Enable ACL](images/enable-acl2.png)

5. mTLS authentication will be set to **Required** after the database automatically restarts.

    ![Enable ACL](images/enable-acl3.png)

6. Navigate to **Tool Configurations** tab and enable **MongoDB API**.

    ![Enable ACL](images/enable-acl4.png)

7. Copy the MongoDB connection URL displayed.

    ![Enable ACL](images/enable-acl5.png)

    The URL format is:
    ``` 
    mongodb://user:<Your-Password>@host:27017/user?authMechanism=PLAIN&authSource=$external&ssl=true&retryWrites=false&loadBalanced=true 
    ```
    
    Where:
    - `user`: Your Oracle Autonomous Database username (e.g., `demouser`)
    - `<Your-Password>`: Your database password (substitute with actual password locally)
    - `host`: Oracle Database hostname from console (e.g., `adb-region.oraclecloudapps.com`)
    - `authMechanism=PLAIN`: Required for Oracle MongoDB API
    - `ssl=true`: Required for TCPS connections

## Task 2: Connect Using Python MongoDB Driver

1. Install the MongoDB Python driver:

    ``` 
    pip install pymongo 
    ```

2. Create a Python script to connect and query data:

    ``` 
    from pymongo import MongoClient

    # Replace with your MongoDB connection URL from Task 1
    # Connection URL format: mongodb://user:<Your-Password>@host:27017/user?authMechanism=PLAIN&authSource=$external&ssl=true&retryWrites=false&loadBalanced=true
    connection_url = "mongodb://user:<Your-Password>@host:27017/user?authMechanism=PLAIN&authSource=$external&ssl=true&retryWrites=false&loadBalanced=true"

    def create_customers_collection(db):
        """Create customers collection with sample data"""
        # Drop existing collection to start fresh
        if 'mycustomers' in db.list_collection_names():
            db['mycustomers'].drop()
            print("✓ Dropped existing mycustomers collection")

        # Create mycustomers collection and insert sample data
        customers_data = [
            {
                "_id": 1,
                "name": "John Smith",
                "email": "john.smith@example.com",
                "city": "New York",
                "phone": "+1-212-555-0100",
                "accountStatus": "active"
            },
            {
                "_id": 2,
                "name": "Sarah Johnson",
                "email": "sarah.johnson@example.com",
                "city": "San Francisco",
                "phone": "+1-415-555-0200",
                "accountStatus": "active"
            },
            {
                "_id": 3,
                "name": "Michael Chen",
                "email": "michael.chen@example.com",
                "city": "Seattle",
                "phone": "+1-206-555-0300",
                "accountStatus": "inactive"
            },
            {
                "_id": 4,
                "name": "Emily Rodriguez",
                "email": "emily.rodriguez@example.com",
                "city": "Austin",
                "phone": "+1-512-555-0400",
                "accountStatus": "active"
            },
            {
                "_id": 5,
                "name": "David Wilson",
                "email": "david.wilson@example.com",
                "city": "Boston",
                "phone": "+1-617-555-0500",
                "accountStatus": "active"
            }
        ]

        result = db['mycustomers'].insert_many(customers_data)
        print(f"✓ Created mycustomers collection with {len(result.inserted_ids)} documents")
        return result

    def query_customer_by_name(db, customer_name):
        """Query customer collection by customer name"""
        customer = db['mycustomers'].find_one({"name": customer_name})
        
        if customer:
            print(f"\n✓ Found customer: {customer_name}")
            print(f"  Email: {customer.get('email')}")
            print(f"  City: {customer.get('city')}")
            print(f"  Phone: {customer.get('phone')}")
            print(f"  Status: {customer.get('accountStatus')}")
            return customer
        else:
            print(f"✗ Customer '{customer_name}' not found")
            return None

    def list_all_customers(db):
        """List all customers in the collection"""
        customers = db['mycustomers'].find()
        print("\n✓ All Customers:")
        for customer in customers:
            print(f"  - {customer['name']} ({customer['email']}) - {customer['city']}")

    try:
        client = MongoClient(connection_url)
        db = client['user']  # Replace 'user' with your database username

        # Verify connection
        print("✓ Connected successfully to Oracle Autonomous AI Database")

        # Create customers collection with sample data
        create_customers_collection(db)

        # List all customers
        list_all_customers(db)

        # Query customers by name
        print("\n" + "="*60)
        print("Querying customers by name:")
        print("="*60)
        
        query_customer_by_name(db, "John Smith")
        query_customer_by_name(db, "Sarah Johnson")
        query_customer_by_name(db, "Jane Doe")  # This customer doesn't exist

    except Exception as e:
        print(f"✗ Connection failed: {e}")
    finally:
        client.close()
        print("\n✓ Database connection closed")  
    ```
 
## Task 3: Connect Using Node.js MongoDB Driver

1. Install the MongoDB Node.js driver:

    ``` 
    npm install mongodb 
    ```

2. Create a Node.js script:

    ```
    <copy>
    const { MongoClient } = require("mongodb");
    
    // Connection URL format: mongodb://user:<Your-Password>@host:27017/user?authMechanism=PLAIN&authSource=$external&ssl=true&retryWrites=false&loadBalanced=true
    const connectionUrl = "mongodb://user:<Your-Password>@host:27017/user?authMechanism=PLAIN&authSource=$external&ssl=true&retryWrites=false&loadBalanced=true";
    
    async function connectAndQuery() {
      const client = new MongoClient(connectionUrl);
      try {
        await client.connect();
        const db = client.db("user");  // Replace 'user' with your database username
        
        // List collections
        const collections = await db.listCollections().toArray();
        console.log(`✓ Connected. Collections:`, collections.map(c => c.name));
        
        // Test query
        if (collections.some(c => c.name === 'customers')) {
          const customer = await db.collection('customers').findOne();
          console.log(`✓ Sample customer:`, customer);
        }
      } catch (err) {
        console.error(`✗ Error:`, err);
      } finally {
        await client.close();
      }
    }
    
    connectAndQuery();
    </copy>
    ```

## Task 4: Connect Using MongoDB Shell 

1. Install MongoDB Shell from [MongoDB documentation](https://www.mongodb.com/docs/mongodb-shell/)

2. Open terminal and create a connection using the URL from Task 1:
 
    ```
    <copy>
    ./mongosh 'mongodb://user:<Your-Password>@host:27017/user?authMechanism=PLAIN&authSource=$external&ssl=true&retryWrites=false&loadBalanced=true'
    </copy>
    ```

    **Note:** If password contains special characters like `#`, URL-encode them (e.g., `#` becomes `%23`)

3. List databases to verify connection:

    ```
    <copy>
    > show dbs
    user  850.91 KiB
    </copy>
    ```
     
4. Insert sample JSON documents:

    ```
    <copy>
    { name: "Storage", price: 80, category: "Accessories", inStock: false }  
    </copy>
    ```

    ![MongoDB APIs](images/api1.png)

5. Find products by category:

    ```
    <copy>
    db.myproducts.find({ category: "Electronics" })
    </copy>
    ``` 
    ![MongoDB APIs](images/api2.png)
     
6. Find all documents in products collection:

    ```
    <copy>
    db.myproducts.find({})
    </copy>
    ```

    ![MongoDB APIs](images/api3.png)
    
7. Find products above a price threshold:

    ```
    <copy>
    db.myproducts.find({ price: { $gt: 300 } })
    </copy>
    ```

    ![MongoDB APIs](images/api4.png)
    

8. Update product price:
    ```
    <copy>
    db.myproducts.updateOne(
    { name: 'Pendrive' }, // filter
    { $set: { price: 1119.99 } } // update
    )
    </copy>
    ```

    ![MongoDB APIs](images/api5.png)
  
## Task 5: Query the Same Data Using SQL Worksheet
  
Oracle's converged database enables querying MongoDB collections directly using SQL. This demonstrates interoperability: store JSON via MongoDB drivers, query with SQL without migration.

1. Open **SQL Worksheet** from Oracle Autonomous Database Console
 
    ```
    <copy>
    SELECT * FROM user.mycustomers
    </copy>
    ```
    
    **Note:** (Please replace `user` with your database username, for example demouser.customers )
 
    ![MongoDB APIs](images/view-customers.png)

    ```
    <copy>
    INSERT INTO user.myproducts (DATA) VALUES
    (
        JSON('{"name": "Mouse", "price": 25, "brand": "Logitech"}') 
    );
    </copy>
    ```

3. Query MongoDB collection using JSON_TABLE and SQL:
    
    ``` 
    <copy>
    SELECT 
        jt.name,
        jt.price,
        jt.category
        FROM user.myproducts p,
    JSON_TABLE(
    p.data, '$' 
    COLUMNS (
        name VARCHAR2(100) PATH '$.name',
        price NUMBER PATH '$.price',
        category VARCHAR2(50) PATH '$.category'
    )
    ) jt
    WHERE jt.price > 300;
    </copy>
    ``` 
    ![Query Results](images/ws1.png)

    **Key Insight:** Store JSON via MongoDB drivers, query with SQL. No ETL or data migration required—single converged database.

## Task 6: Connect  to Oracle MongoDB API Using Google Colab Notebook

1. Download and Run [Google Colab Notebook](mongodb_create_customers.ipynb)

2. Install the required libraries

    ```
    <copy>
    !pip install pymongo
    </copy>
    ```

3. Get the Public IP of Google Colab Notebook and Add it to Allowed ACL list

    ```
    <copy>
    !curl ipecho.net/plain
    </copy>
    ```

    ![Enable ACL](images/enable-acl2.png)

4. Check if pymongo is installed

    ```
    <copy>
    import subprocess
    import sys

    try:
        import pymongo
        print("✓ pymongo is already installed")
    except ImportError:
        print("Installing pymongo...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pymongo"])
        print("✓ pymongo installed successfully")
    </copy>
    ```

5. Setup Configuration variables. Replace with your MongoDB connection details. Get these values from Oracle Cloud Console → Autonomous Database → Tool Configurations → MongoDB API

    ```
    <copy>
    # MongoDB connection parameters
    MONGO_HOST = "R9NV7IFXZVF7RHN-INDEDUCATION.adb.ap-mumbai-1.oraclecloudapps.com"  # Replace with your host
    MONGO_PORT = 27017
    MONGO_USER = "demouser"  # Replace with your database username
    MONGO_PASSWORD = ""  # Replace with your actual password
    MONGO_DB = "demouser"  # Replace with your database username (same as user in most cases)
    MONGO_AUTH_MECHANISM = "PLAIN"

    # Construct MongoDB connection URL
    connection_url = f"mongodb://{MONGO_USER}:{MONGO_PASSWORD}@{MONGO_HOST}:{MONGO_PORT}/{MONGO_DB}?authMechanism={MONGO_AUTH_MECHANISM}&authSource=$external&ssl=true&retryWrites=false&loadBalanced=true"

    print("✓ Configuration loaded")
    print(f"  Host: {MONGO_HOST}")
    print(f"  User: {MONGO_USER}")
    print(f"  Database: {MONGO_DB}")
        
    </copy>
    ```

6. Create customers, List customers and View all customers

    ```
    <copy>
    from pymongo import MongoClient

    def create_customers_collection(db):
        """Create customers collection with sample data"""
        # Drop existing collection to start fresh
        if 'mycustomers' in db.list_collection_names():
            db['mycustomers'].drop()
            print("✓ Dropped existing mycustomers collection")

        # Create mycustomers collection and insert sample data
        customers_data = [
            {
                "_id": 1,
                "name": "John Smith",
                "email": "john.smith@example.com",
                "city": "New York",
                "phone": "+1-212-555-0100",
                "accountStatus": "active"
            },
            {
                "_id": 2,
                "name": "Sarah Johnson",
                "email": "sarah.johnson@example.com",
                "city": "San Francisco",
                "phone": "+1-415-555-0200",
                "accountStatus": "active"
            },
            {
                "_id": 3,
                "name": "Michael Chen",
                "email": "michael.chen@example.com",
                "city": "Seattle",
                "phone": "+1-206-555-0300",
                "accountStatus": "inactive"
            },
            {
                "_id": 4,
                "name": "Emily Rodriguez",
                "email": "emily.rodriguez@example.com",
                "city": "Austin",
                "phone": "+1-512-555-0400",
                "accountStatus": "active"
            },
            {
                "_id": 5,
                "name": "David Wilson",
                "email": "david.wilson@example.com",
                "city": "Boston",
                "phone": "+1-617-555-0500",
                "accountStatus": "active"
            }
        ]

        result = db['mycustomers'].insert_many(customers_data)
        print(f"✓ Created mycustomers collection with {len(result.inserted_ids)} documents")
        return result

    def query_customer_by_name(db, customer_name):
        """Query customer collection by customer name"""
        customer = db['mycustomers'].find_one({"name": customer_name})

        if customer:
            print(f"\n✓ Found customer: {customer_name}")
            print(f"  Email: {customer.get('email')}")
            print(f"  City: {customer.get('city')}")
            print(f"  Phone: {customer.get('phone')}")
            print(f"  Status: {customer.get('accountStatus')}")
            return customer
        else:
            print(f"✗ Customer '{customer_name}' not found")
            return None

    def list_all_customers(db):
        """List all customers in the collection"""
        customers = db['mycustomers'].find()
        print("\n✓ All Customers:")
        for customer in customers:
            print(f"  - {customer['name']} ({customer['email']}) - {customer['city']}")

    print("✓ Helper functions defined")
    </copy>
    ```

7. Connect to Oracle Database using MongoDB API Connection string and list customers

    ```
    <copy>
    try:
    # Connect to Database
    client = MongoClient(connection_url)
    db = client[MONGO_DB]

    # Verify connection
    print("✓ Connected successfully to Oracle Autonomous AI Database")

    # Create customers collection with sample data
    create_customers_collection(db)

    # List all customers
    list_all_customers(db)

    # Query customers by name
    print("\n" + "="*60)
    print("Querying customers by name:")
    print("="*60)

    query_customer_by_name(db, "John Smith")
    query_customer_by_name(db, "Sarah Johnson")
    query_customer_by_name(db, "Jane Doe")  # This customer doesn't exist

    except Exception as e:
        print(f"✗ Connection failed: {e}")
        print("\nTroubleshooting tips:")
        print("1. Verify MongoDB API is enabled in Oracle Cloud Console")
        print("2. Check connection URL format and credentials")
        print("3. Ensure your IP is in the database access control list")
    finally:
        if 'client' in locals():
            client.close()
            print("\n✓ Database connection closed")
    </copy>
    ```

    Run the Google Colab Notebook
    
    ![Run Colab Notebook](images/run.png)
 
## Learn More

* [Oracle Database API for MongoDB Documentation](https://docs.oracle.com/en-us/iaas/autonomous-database-serverless/doc/oracle-database-api-mongodb.html)
* [JSON Relational Duality Views Documentation](https://docs.oracle.com/en-us/iaas/autonomous-database-serverless/doc/json-relational-duality-views.html)
* [Autonomous AI Database for Developers](https://docs.oracle.com/en-us/iaas/autonomous-database-serverless/doc/autonomous-database-for-developers.html)
* [MongoDB Python Driver Documentation](https://pymongo.readthedocs.io/)
* [MongoDB Node.js Driver Documentation](https://www.mongodb.com/docs/drivers/node/)
* [Download All Source Code](https://github.com/madhusudhanrao-ppm/dbdevrel/tree/main/source-codes)
* [Autonomous AI Database Billing](https://docs.oracle.com/en-us/iaas/autonomous-database-serverless/doc/autonomous-database-for-developers-billing.html)
 