import os
import pg8000
import sqlalchemy

from google.cloud.sql.connector import Connector, IPTypes
from dotenv import load_dotenv

def connect_with_connector_auto_iam_authn() -> sqlalchemy.engine.base.Engine:
    """
    Initializes a connection pool for a Cloud SQL instance of PostgreSQL.

    Uses the Cloud SQL Python Connector with Automatic IAM Database Authentication.
    """
    load_dotenv()

    instance_connection_name = os.environ[
        "INSTANCE_CONNECTION_NAME"
    ]  # e.g. 'project:region:instance'
    db_iam_user = os.environ["DB_IAM_USER"]  # e.g. 'service-account-name'
    db_name = os.environ["DB_NAME"]  # e.g. 'my-database'

    ip_type = IPTypes.PRIVATE if os.environ.get("PRIVATE_IP") else IPTypes.PUBLIC

    connector = Connector()

    def getconn() -> pg8000.Connection:
        conn: pg8000.Connection = connector.connect(
            instance_connection_name,
            "pg8000",
            user=db_iam_user,
            db=db_name,
            enable_iam_auth=True,
            ip_type=ip_type,
        )
        return conn

    pool = sqlalchemy.create_engine(
        "postgresql+pg8000://",
        creator=getconn,
        pool_size=60,
        max_overflow=10,
        pool_timeout=90,  # 30 seconds
        pool_recycle=1800,  # 30 minutes
    )
    return pool

# [END cloud_sql_postgres_sqlalchemy_auto_iam_authn]
