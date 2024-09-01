import os

from google.cloud.sql.connector import Connector, IPTypes
import pg8000

import sqlalchemy
from dotenv import load_dotenv
from .settings import DB_USER, DB_PASSWORD, DB_INSTANCE_CONNECTION_NAME, DB_NAME, DB_PORT

def connect_with_connector() -> sqlalchemy.engine.base.Engine:
    """
    Initializes a connection pool for a Cloud SQL instance of PostgreSQL.

    Uses the Cloud SQL Python Connector package.
    """
    load_dotenv()

    ip_type = IPTypes.PRIVATE if os.environ.get("PRIVATE_IP") else IPTypes.PUBLIC

    connector = Connector(ip_type)

    def getconn() -> pg8000.Connection:
        conn: pg8000.Connection = connector.connect(
            DB_INSTANCE_CONNECTION_NAME,
            "pg8000",
            user=DB_USER,
            password=DB_PASSWORD
            db=DB_NAME_TANTEA,
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

# [END cloud_sql_postgres_sqlalchemy_connect_connector]
