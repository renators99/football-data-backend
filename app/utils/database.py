from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.utils.secrets import get_secret

# Recuperar los secretos desde GCP
db_user = get_secret("DB_USER")
db_password = get_secret("DB_PASSWORD")
db_host = get_secret("DB_HOST")
db_name = get_secret("DB_NAME")

# Construir la URL de la base de datos
DATABASE_URL = f"postgresql+psycopg2://{db_user}:{db_password}@{db_host}/{db_name}"

# Crear el motor de la base de datos
engine = create_engine(DATABASE_URL)

# Crear la sesión local de SQLAlchemy
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Declarar la base para los modelos de SQLAlchemy
Base = declarative_base()

def init_db():
    """
    Inicializa la base de datos creando todas las tablas definidas en los modelos.
    """
    Base.metadata.create_all(bind=engine)
