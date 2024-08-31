import os
from google.cloud import secretmanager

def access_secret_version(project_id, secret_id, version_id="latest"):
    """
    Access the secret version from Google Cloud Secret Manager.
    """
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{project_id}/secrets/{secret_id}/versions/{version_id}"
    response = client.access_secret_version(name=name)
    return response.payload.data.decode('UTF-8')

def load_secrets():
    project_id = "upbeat-voice-433617"
    
    # Add your secret names here
    db_url_secret_name = "DATABASE_URL"

    # Load the secrets
    database_url = access_secret_version(project_id, db_url_secret_name)
    
    return {
        "DATABASE_URL": database_url,
    }
