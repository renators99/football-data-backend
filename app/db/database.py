import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .connect_tcp import connect_tcp_socket
from .connect_unix import connect_unix_socket
from .connect_connector_auto_iam_authn import connect_with_connector_auto_iam_authn
from .connect_connector import connect_with_connector
from .settings import get_db_url

# Función para crear el motor de la base de datos
def create_db_engine():
    """
    Intenta crear un engine utilizando diferentes métodos de conexión.
    """
    try:
        # Intentar la conexión mediante TCP
        return connect_tcp_socket()
    except Exception as e:
        print(f"Fallo en conexión TCP: {e}")

    try:
        # Intentar la conexión mediante Unix Socket
        return connect_unix_socket()
    except Exception as e:
        print(f"Fallo en conexión Unix Socket: {e}")

    try:
        # Intentar la conexión mediante Cloud SQL Connector con autenticación IAM automática
        return connect_with_connector_auto_iam_authn()
    except Exception as e:
        print(f"Fallo en conexión Cloud SQL Connector IAM: {e}")

    try:
        # Intentar la conexión mediante Cloud SQL Connector normal
        return connect_with_connector()
    except Exception as e:
        print(f"Fallo en conexión Cloud SQL Connector: {e}")

    # Como último recurso, intenta con la URL directa de la base de datos
    return create_engine(get_db_url())

# Crear el motor de la base de datos
engine = create_db_engine()

# Crear la sesión local de SQLAlchemy
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """
    Inicializa la base de datos creando todas las tablas definidas en los modelos.
    """
    from .base import Base  # Importar Base aquí para evitar importaciones circulares
    Base.metadata.create_all(bind=engine)
