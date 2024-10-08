import os
import sqlalchemy
from dotenv import load_dotenv

def connect_unix_socket() -> sqlalchemy.engine.base.Engine:
    """Initializes a Unix socket connection pool for a Cloud SQL instance of PostgreSQL."""
    # Note: Saving credentials in environment variables is convenient, but not
    # secure - consider a more secure solution such as
    # Cloud Secret Manager (https://cloud.google.com/secret-manager) to help
    # keep secrets safe.
    load_dotenv()

    db_user = os.environ["DB_USER"]  # e.g. 'my-database-user'
    db_pass = os.environ["DB_PASS"]  # e.g. 'my-database-password'
    db_name = os.environ["DB_NAME"]  # e.g. 'my-database'
    unix_socket_path = os.environ[
        "INSTANCE_UNIX_SOCKET"
    ]  # e.g. '/cloudsql/project:region:instance'

    pool = sqlalchemy.create_engine(
        # Equivalent URL:
        # postgresql+psycopg2://<db_user>:<db_pass>@/<db_name>?host=/cloudsql/<cloud_sql_instance_name>
        sqlalchemy.engine.url.URL.create(
            drivername="postgresql+psycopg2",
            username=db_user,
            password=db_pass,
            database=db_name,
            query={"host": unix_socket_path},
        ),
        # [START_EXCLUDE]
        # Pool size is the maximum number of permanent connections to keep.
        pool_size=60,
        # Temporarily exceeds the set pool_size if no connections are available.
        max_overflow=10,
        # The total number of concurrent connections for your application will be
        # a total of pool_size and max_overflow.
        # 'pool_timeout' is the maximum number of seconds to wait when retrieving a
        # new connection from the pool. After the specified amount of time, an
        # exception will be thrown.
        pool_timeout=90,  # 30 seconds
        # 'pool_recycle' is the maximum number of seconds a connection can persist.
        # Connections that live longer than the specified amount of time will be
        # re-established
        pool_recycle=1800,  # 30 minutes
        # [END_EXCLUDE]
    )
    return pool
