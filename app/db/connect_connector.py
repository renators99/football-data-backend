from google.cloud.sql.connector import Connector, IPTypes
import sqlalchemy
from app.utils.secrets import get_secret

def connect_with_connector() -> sqlalchemy.engine.base.Engine:
    """
    Initializes a connection pool for a Cloud SQL instance of PostgreSQL.
    """
    # Recuperar los secretos desde GCP
    db_user = get_secret("DB_USER")
    db_password = get_secret("DB_PASSWORD")
    db_name = get_secret("DB_NAME")
    db_port = get_secret("DB_PORT")  # Asegúrate de que este valor sea un entero
    db_instance_connection_name = get_secret("DB_INSTANCE_CONNECTION_NAME")

    connector = Connector()

    def getconn() -> sqlalchemy.engine.base.Connection:
        conn: sqlalchemy.engine.base.Connection = connector.connect(
            db_instance_connection_name,
            "pg8000",
            user=db_user,
            password=db_password,
            db=db_name,
        )
        return conn

    # Crear el pool de conexiones usando SQLAlchemy
    pool = sqlalchemy.create_engine(
        f"postgresql+pg8000://",
        creator=getconn,
        pool_size=5,
        max_overflow=2,
        pool_timeout=30,
        pool_recycle=1800,
    )
    return pool
