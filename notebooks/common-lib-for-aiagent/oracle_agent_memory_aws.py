"""
AWS Oracle Database Memory Store for AI Agents
Extends oracle_agent_memory.py for AWS RDS Oracle deployment

This module provides AWS-specific configurations and integrations:
- AWS RDS Oracle database connectivity
- AWS IAM database authentication
- AWS Secrets Manager for credential management
- VPC and security group configuration
- CloudWatch integration for monitoring
- Deployment patterns for AWS Lambda, ECS, EC2
"""

import json
import os
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
import boto3
from botocore.exceptions import ClientError

from oracle_agent_memory import (
    OracleMemoryConfig,
    create_oracle_agent_memory,
    OracleAgentMemory,
    test_oracle_connection,
)


# ============================================================================
# 1. AWS RDS Oracle Configuration
# ============================================================================

class AWSRDSOracleConfig:
    """AWS RDS Oracle-specific configuration"""
    
    def __init__(
        self,
        db_instance_identifier: str,
        db_endpoint: str,
        port: int = 1521,
        db_name: str = "ORCL",
        aws_region: str = "us-east-1",
        use_iam_auth: bool = True,
    ):
        """
        Initialize AWS RDS Oracle configuration.
        
        Args:
            db_instance_identifier: RDS instance identifier (e.g., 'oracle-prod-db')
            db_endpoint: RDS endpoint hostname (e.g., 'mydb.xxxxx.us-east-1.rds.amazonaws.com')
            port: Database port (default 1521 for Oracle)
            db_name: Database name/SID (default ORCL)
            aws_region: AWS region
            use_iam_auth: Whether to use IAM database authentication
        """
        self.db_instance_identifier = db_instance_identifier
        self.db_endpoint = db_endpoint
        self.port = port
        self.db_name = db_name
        self.aws_region = aws_region
        self.use_iam_auth = use_iam_auth
        self.rds_client = boto3.client("rds", region_name=aws_region)
        self.secretsmanager_client = boto3.client("secretsmanager", region_name=aws_region)
    
    def get_rds_instance_info(self) -> Dict:
        """
        Retrieve RDS instance information from AWS.
        
        Returns:
            Dictionary with instance details
        """
        try:
            response = self.rds_client.describe_db_instances(
                DBInstanceIdentifier=self.db_instance_identifier
            )
            instance = response["DBInstances"][0]
            return {
                "endpoint": instance["Endpoint"]["Address"],
                "port": instance["Endpoint"]["Port"],
                "status": instance["DBInstanceStatus"],
                "engine": instance["Engine"],
                "engine_version": instance["EngineVersion"],
                "allocated_storage": instance.get("AllocatedStorage"),
                "db_instance_class": instance["DBInstanceClass"],
            }
        except ClientError as e:
            print(f"Error retrieving RDS instance info: {e}")
            return {}
    
    def get_credentials_from_secrets_manager(self, secret_name: str) -> Tuple[str, str]:
        """
        Retrieve database credentials from AWS Secrets Manager.
        
        Args:
            secret_name: Name of the secret in Secrets Manager
            
        Returns:
            Tuple of (username, password)
        """
        try:
            response = self.secretsmanager_client.get_secret_value(SecretId=secret_name)
            
            if "SecretString" in response:
                secret = json.loads(response["SecretString"])
                username = secret.get("username")
                password = secret.get("password")
                return username, password
            else:
                raise ValueError("Secret is binary, expected JSON format")
        except ClientError as e:
            print(f"Error retrieving secret from Secrets Manager: {e}")
            raise
    
    def create_iam_auth_token(self, db_user: str) -> str:
        """
        Generate AWS IAM database authentication token.
        Token is valid for 15 minutes.
        
        Args:
            db_user: Database username (must be created with IAM auth)
            
        Returns:
            Authentication token for database connection
        """
        try:
            token = self.rds_client.generate_db_auth_token(
                DBHostname=self.db_endpoint,
                Port=self.port,
                DBUser=db_user,
                Region=self.aws_region,
            )
            return token
        except ClientError as e:
            print(f"Error generating IAM auth token: {e}")
            raise
    
    def to_oracle_config(
        self,
        username: str,
        password: Optional[str] = None,
        use_iam_token: bool = False,
    ) -> OracleMemoryConfig:
        """
        Convert AWS RDS config to OracleMemoryConfig.
        
        Args:
            username: Database username
            password: Database password (not needed if using IAM)
            use_iam_token: Whether to use IAM token instead of password
            
        Returns:
            OracleMemoryConfig instance configured for RDS
        """
        if use_iam_token:
            password = self.create_iam_auth_token(username)
        
        return OracleMemoryConfig(
            username=username,
            password=password,
            host=self.db_endpoint,
            port=self.port,
            sid=self.db_name,
        )


# ============================================================================
# 2. AWS Environment-Based Configuration
# ============================================================================

class AWSEnvironmentConfig:
    """Load configuration from AWS environment variables and Secrets Manager"""
    
    @staticmethod
    def from_environment() -> Tuple[AWSRDSOracleConfig, str, str]:
        """
        Create AWS RDS config from environment variables.
        
        Expected environment variables:
        - AWS_REGION: AWS region
        - RDS_ORACLE_ENDPOINT: RDS hostname
        - RDS_ORACLE_INSTANCE_ID: RDS instance identifier
        - RDS_ORACLE_PORT: Database port (default 1521)
        - RDS_ORACLE_DB_NAME: Database name (default ORCL)
        - RDS_DB_SECRET_NAME: Secrets Manager secret name
        - RDS_DB_USERNAME: Override username (optional)
        
        Returns:
            Tuple of (AWSRDSOracleConfig, username, password)
        """
        aws_region = os.getenv("AWS_REGION", "us-east-1")
        db_endpoint = os.getenv("RDS_ORACLE_ENDPOINT")
        db_instance_id = os.getenv("RDS_ORACLE_INSTANCE_ID")
        db_port = int(os.getenv("RDS_ORACLE_PORT", "1521"))
        db_name = os.getenv("RDS_ORACLE_DB_NAME", "ORCL")
        secret_name = os.getenv("RDS_DB_SECRET_NAME")
        
        if not db_endpoint:
            raise ValueError("RDS_ORACLE_ENDPOINT environment variable not set")
        if not db_instance_id:
            raise ValueError("RDS_ORACLE_INSTANCE_ID environment variable not set")
        if not secret_name:
            raise ValueError("RDS_DB_SECRET_NAME environment variable not set")
        
        aws_rds_config = AWSRDSOracleConfig(
            db_instance_identifier=db_instance_id,
            db_endpoint=db_endpoint,
            port=db_port,
            db_name=db_name,
            aws_region=aws_region,
        )
        
        # Get credentials from Secrets Manager
        username, password = aws_rds_config.get_credentials_from_secrets_manager(secret_name)
        
        return aws_rds_config, username, password
    
    @staticmethod
    def from_iam_auth() -> Tuple[AWSRDSOracleConfig, str, str]:
        """
        Create AWS RDS config using IAM database authentication.
        
        Expected environment variables:
        - AWS_REGION
        - RDS_ORACLE_ENDPOINT
        - RDS_ORACLE_INSTANCE_ID
        - RDS_DB_IAM_USER: IAM database user (must be created in Oracle with IAM auth)
        
        Returns:
            Tuple of (AWSRDSOracleConfig, username, iam_token)
        """
        aws_region = os.getenv("AWS_REGION", "us-east-1")
        db_endpoint = os.getenv("RDS_ORACLE_ENDPOINT")
        db_instance_id = os.getenv("RDS_ORACLE_INSTANCE_ID")
        iam_user = os.getenv("RDS_DB_IAM_USER")
        
        if not all([db_endpoint, db_instance_id, iam_user]):
            raise ValueError("Missing required IAM auth environment variables")
        
        aws_rds_config = AWSRDSOracleConfig(
            db_instance_identifier=db_instance_id,
            db_endpoint=db_endpoint,
            aws_region=aws_region,
            use_iam_auth=True,
        )
        
        # Generate IAM token
        iam_token = aws_rds_config.create_iam_auth_token(iam_user)
        
        return aws_rds_config, iam_user, iam_token


# ============================================================================
# 3. AWS Agent Memory Factory
# ============================================================================

class AWSOracleAgentMemoryFactory:
    """Factory for creating agent memory with AWS RDS Oracle"""
    
    @staticmethod
    def create_from_secrets_manager(
        db_instance_identifier: str,
        db_endpoint: str,
        secret_name: str,
        session_id: str,
        agent_id: str = "default_agent",
        aws_region: str = "us-east-1",
    ) -> OracleAgentMemory:
        """
        Create agent memory using credentials from AWS Secrets Manager.
        
        Args:
            db_instance_identifier: RDS instance ID
            db_endpoint: RDS endpoint hostname
            secret_name: Secrets Manager secret name
            session_id: Conversation session ID
            agent_id: Agent identifier
            aws_region: AWS region
            
        Returns:
            OracleAgentMemory instance connected to RDS Oracle
        """
        aws_rds_config = AWSRDSOracleConfig(
            db_instance_identifier=db_instance_identifier,
            db_endpoint=db_endpoint,
            aws_region=aws_region,
        )
        
        # Retrieve credentials
        username, password = aws_rds_config.get_credentials_from_secrets_manager(secret_name)
        
        # Convert to OracleMemoryConfig
        oracle_config = aws_rds_config.to_oracle_config(username, password)
        
        # Create and return agent memory
        return create_oracle_agent_memory(
            oracle_config=oracle_config,
            session_id=session_id,
            agent_id=agent_id,
        )
    
    @staticmethod
    def create_from_iam_auth(
        db_instance_identifier: str,
        db_endpoint: str,
        db_user: str,
        session_id: str,
        agent_id: str = "default_agent",
        aws_region: str = "us-east-1",
    ) -> OracleAgentMemory:
        """
        Create agent memory using AWS IAM database authentication.
        
        Args:
            db_instance_identifier: RDS instance ID
            db_endpoint: RDS endpoint hostname
            db_user: IAM database user (must be created with IAM auth in Oracle)
            session_id: Conversation session ID
            agent_id: Agent identifier
            aws_region: AWS region
            
        Returns:
            OracleAgentMemory instance with IAM authentication
        """
        aws_rds_config = AWSRDSOracleConfig(
            db_instance_identifier=db_instance_identifier,
            db_endpoint=db_endpoint,
            aws_region=aws_region,
            use_iam_auth=True,
        )
        
        # Convert to OracleMemoryConfig with IAM token
        oracle_config = aws_rds_config.to_oracle_config(
            username=db_user,
            use_iam_token=True,
        )
        
        # Create and return agent memory
        return create_oracle_agent_memory(
            oracle_config=oracle_config,
            session_id=session_id,
            agent_id=agent_id,
        )
    
    @staticmethod
    def create_from_environment(
        session_id: str,
        agent_id: str = "default_agent",
    ) -> OracleAgentMemory:
        """
        Create agent memory from environment variables.
        
        Automatically detects IAM auth or Secrets Manager based on variables.
        
        Args:
            session_id: Conversation session ID
            agent_id: Agent identifier
            
        Returns:
            OracleAgentMemory instance
        """
        use_iam = os.getenv("RDS_DB_IAM_USER") is not None
        
        if use_iam:
            aws_rds_config, username, iam_token = AWSEnvironmentConfig.from_iam_auth()
        else:
            aws_rds_config, username, password = AWSEnvironmentConfig.from_environment()
        
        oracle_config = aws_rds_config.to_oracle_config(
            username=username,
            password=None if use_iam else password,
            use_iam_token=use_iam,
        )
        
        return create_oracle_agent_memory(
            oracle_config=oracle_config,
            session_id=session_id,
            agent_id=agent_id,
        )


# ============================================================================
# 4. AWS CloudWatch Monitoring
# ============================================================================

class AWSMemoryMonitoring:
    """CloudWatch monitoring for agent memory operations"""
    
    def __init__(self, aws_region: str = "us-east-1"):
        """Initialize CloudWatch client"""
        self.cloudwatch = boto3.client("cloudwatch", region_name=aws_region)
        self.namespace = "OracleAgentMemory"
    
    def log_metric(
        self,
        metric_name: str,
        value: float,
        unit: str = "Count",
        dimensions: Optional[Dict] = None,
    ) -> None:
        """
        Log custom metric to CloudWatch.
        
        Args:
            metric_name: Name of the metric
            value: Metric value
            unit: Unit of measurement
            dimensions: Optional dimensions dict
        """
        try:
            metric_data = {
                "MetricName": metric_name,
                "Value": value,
                "Unit": unit,
                "Timestamp": datetime.utcnow(),
            }
            
            if dimensions:
                metric_data["Dimensions"] = [
                    {"Name": k, "Value": str(v)} for k, v in dimensions.items()
                ]
            
            self.cloudwatch.put_metric_data(
                Namespace=self.namespace,
                MetricData=[metric_data],
            )
        except ClientError as e:
            print(f"Error logging metric to CloudWatch: {e}")
    
    def log_conversation_length(
        self,
        session_id: str,
        message_count: int,
        agent_id: str = "default_agent",
    ) -> None:
        """Log conversation length metric"""
        self.log_metric(
            metric_name="ConversationLength",
            value=message_count,
            dimensions={"SessionId": session_id, "AgentId": agent_id},
        )
    
    def log_db_operation_time(
        self,
        operation_name: str,
        duration_ms: float,
        session_id: str,
    ) -> None:
        """Log database operation duration"""
        self.log_metric(
            metric_name=f"{operation_name}Duration",
            value=duration_ms,
            unit="Milliseconds",
            dimensions={"SessionId": session_id},
        )


# ============================================================================
# 5. Deployment Scripts for AWS Lambda
# ============================================================================

class AWSLambdaMemoryHandler:
    """Lambda function handler for AI agent with Oracle memory"""
    
    def __init__(self, aws_region: str = "us-east-1"):
        """Initialize Lambda handler"""
        self.aws_region = aws_region
        self.monitoring = AWSMemoryMonitoring(aws_region)
    
    def create_lambda_handler(self, session_id_source: str = "requestContext"):
        """
        Create Lambda handler function for agent requests.
        
        Args:
            session_id_source: Where to extract session ID from
            
        Returns:
            Handler function compatible with AWS Lambda
        """
        def lambda_handler(event, context):
            """
            AWS Lambda handler for AI agent with Oracle memory.
            
            Expected event structure:
            {
                "body": {
                    "message": "User message",
                    "session_id": "user-session-123",
                    "agent_id": "chat_agent"
                }
            }
            """
            try:
                # Parse input
                if isinstance(event.get("body"), str):
                    body = json.loads(event["body"])
                else:
                    body = event.get("body", {})
                
                message = body.get("message")
                session_id = body.get("session_id")
                agent_id = body.get("agent_id", "default_agent")
                
                if not all([message, session_id]):
                    return {
                        "statusCode": 400,
                        "body": json.dumps({"error": "Missing required fields"}),
                    }
                
                # Create agent memory from environment
                memory = AWSOracleAgentMemoryFactory.create_from_environment(
                    session_id=session_id,
                    agent_id=agent_id,
                )
                
                # Process message (placeholder for actual agent logic)
                start_time = datetime.utcnow()
                
                # Simulate agent processing
                history = memory.get_conversation_history(limit=5)
                
                # Log metrics
                duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
                self.monitoring.log_db_operation_time(
                    "GetHistory",
                    duration_ms,
                    session_id,
                )
                
                return {
                    "statusCode": 200,
                    "body": json.dumps({
                        "message": "Success",
                        "history_count": len(history),
                        "session_id": session_id,
                    }),
                }
            
            except Exception as e:
                print(f"Error in Lambda handler: {str(e)}")
                return {
                    "statusCode": 500,
                    "body": json.dumps({"error": str(e)}),
                }
        
        return lambda_handler


# ============================================================================
# 6. Complete Usage Examples with AWS
# ============================================================================

if __name__ == "__main__":
    """
    Examples for using Oracle Agent Memory with AWS RDS Oracle
    """
    
    print("=" * 80)
    print("AWS RDS Oracle Agent Memory Examples")
    print("=" * 80)
    
    # ========================================================================
    # Example 1: Using AWS Secrets Manager
    # ========================================================================
    print("\n" + "=" * 80)
    print("Example 1: Oracle Agent Memory with AWS Secrets Manager")
    print("=" * 80)
    
    try:
        memory = AWSOracleAgentMemoryFactory.create_from_secrets_manager(
            db_instance_identifier="oracle-prod-db",
            db_endpoint="mydb.xxxxx.us-east-1.rds.amazonaws.com",
            secret_name="rds/oracle/credentials",
            session_id="chat_session_001",
            agent_id="aws_chat_agent",
            aws_region="us-east-1",
        )
        print("✓ Agent memory created from Secrets Manager")
        print(f"  Session ID: {memory.session_id}")
        print(f"  Agent ID: {memory.agent_id}")
    except Exception as e:
        print(f"Note: {e}")
        print("  Make sure AWS credentials are configured and RDS instance exists")
    
    # ========================================================================
    # Example 2: Using IAM Database Authentication
    # ========================================================================
    print("\n" + "=" * 80)
    print("Example 2: Oracle Agent Memory with IAM Authentication")
    print("=" * 80)
    
    try:
        memory = AWSOracleAgentMemoryFactory.create_from_iam_auth(
            db_instance_identifier="oracle-prod-db",
            db_endpoint="mydb.xxxxx.us-east-1.rds.amazonaws.com",
            db_user="iamuser",
            session_id="iam_session_001",
            agent_id="iam_agent",
            aws_region="us-east-1",
        )
        print("✓ Agent memory created with IAM authentication")
        print(f"  Session ID: {memory.session_id}")
        print(f"  Using IAM authentication (token-based, 15-minute expiry)")
    except Exception as e:
        print(f"Note: {e}")
    
    # ========================================================================
    # Example 3: Environment-Based Configuration
    # ========================================================================
    print("\n" + "=" * 80)
    print("Example 3: Load from Environment Variables")
    print("=" * 80)
    
    print("""
Expected environment variables:
  - AWS_REGION: AWS region (default: us-east-1)
  - RDS_ORACLE_ENDPOINT: RDS hostname
  - RDS_ORACLE_INSTANCE_ID: RDS instance identifier
  - RDS_DB_SECRET_NAME: Secrets Manager secret name (for credential auth)
  - RDS_DB_IAM_USER: IAM user name (for IAM auth)
    """)
    
    try:
        memory = AWSOracleAgentMemoryFactory.create_from_environment(
            session_id="env_session_001",
            agent_id="env_agent",
        )
        print("✓ Agent memory created from environment variables")
    except ValueError as e:
        print(f"Note: {e}")
    
    # ========================================================================
    # Example 4: RDS Instance Information
    # ========================================================================
    print("\n" + "=" * 80)
    print("Example 4: Retrieve RDS Instance Information")
    print("=" * 80)
    
    try:
        rds_config = AWSRDSOracleConfig(
            db_instance_identifier="oracle-prod-db",
            db_endpoint="mydb.xxxxx.us-east-1.rds.amazonaws.com",
            aws_region="us-east-1",
        )
        
        info = rds_config.get_rds_instance_info()
        if info:
            print("✓ RDS Instance Information:")
            for key, value in info.items():
                print(f"  {key}: {value}")
    except Exception as e:
        print(f"Note: {e}")
    
    # ========================================================================
    # Example 5: CloudWatch Monitoring
    # ========================================================================
    print("\n" + "=" * 80)
    print("Example 5: CloudWatch Monitoring")
    print("=" * 80)
    
    try:
        monitoring = AWSMemoryMonitoring(aws_region="us-east-1")
        
        # Log some metrics
        monitoring.log_conversation_length(
            session_id="session_001",
            message_count=42,
            agent_id="chat_agent",
        )
        
        monitoring.log_db_operation_time(
            "QueryExecution",
            duration_ms=245.5,
            session_id="session_001",
        )
        
        print("✓ Custom metrics sent to CloudWatch")
        print("  - ConversationLength: 42 messages")
        print("  - QueryExecutionDuration: 245.5 ms")
    except Exception as e:
        print(f"Note: {e}")
    
    # ========================================================================
    # Example 6: AWS Lambda Handler
    # ========================================================================
    print("\n" + "=" * 80)
    print("Example 6: AWS Lambda Handler")
    print("=" * 80)
    
    handler = AWSLambdaMemoryHandler(aws_region="us-east-1")
    lambda_handler = handler.create_lambda_handler()
    
    print("✓ Lambda handler created")
    print("""
Usage in Lambda function:
    from oracle_agent_memory_aws import AWSLambdaMemoryHandler
    
    handler = AWSLambdaMemoryHandler()
    lambda_handler = handler.create_lambda_handler()
    
Event payload:
    {
        "body": {
            "message": "What is in my conversation history?",
            "session_id": "user-123",
            "agent_id": "chat_agent"
        }
    }
    """)
    
    print("\n" + "=" * 80)
    print("Examples completed!")
    print("=" * 80)
