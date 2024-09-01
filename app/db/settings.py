from app.utils.secrets import get_secret

def get_db_url():
    """
    Construye la URL de la base de datos utilizando los secretos almacenados en GCP.
    """
    # Recuperar los secretos desde GCP
    db_user = get_secret("DB_USER")
    db_password = get_secret("DB_PASSWORD")
    db_host = get_secret("DB_HOST")
    db_name = get_secret("DB_NAME")
    db_port = get_secret("DB_PORT")

    # Construir la URL de la base de datos incluyendo el puerto
    return f"postgresql+psycopg2://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
