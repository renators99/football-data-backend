from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .settings import get_db_url

# Crear el motor de la base de datos usando la URL obtenida de settings.py
engine = create_engine(get_db_url())

# Crear la sesión local de SQLAlchemy
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """
    Inicializa la base de datos creando todas las tablas definidas en los modelos.
    """
    from .base import Base  # Importar Base aquí para evitar importaciones circulares
    Base.metadata.create_all(bind=engine)
