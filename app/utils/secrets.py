from google.cloud import secretmanager

def get_secret(secret_name: str, project_id: str = "upbeat-voice-433617-n9") -> str:
    """
    Recupera un secreto de Google Cloud Secret Manager.
    
    Args:
        secret_name (str): El nombre del secreto que quieres recuperar.
        project_id (str): El ID del proyecto GCP. Por defecto, se usa el proyecto configurado.

    Returns:
        str: El valor del secreto.
    """
    client = secretmanager.SecretManagerServiceClient()
    
    # Construir el nombre completo del recurso
    secret_name = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
    
    # Acceder al secreto
    response = client.access_secret_version(request={"name": secret_name})
    
    # Retornar el valor del secreto (response.payload.data es en bytes, así que se convierte a string)
    return response.payload.data.decode("UTF-8")
