import os
import google.cloud.secretmanager as secretmanager

def get_secret(secret_id):
    project_id = "upbeat-voice-433617-n9"  # Reemplaza esto con tu project ID si es diferente
    client = secretmanager.SecretManagerServiceClient()
    response = client.access_secret_version(
        name=f"projects/{project_id}/secrets/{secret_id}/versions/latest"  # Usa "latest" para obtener la última versión
    )
    return response.payload.data.decode("UTF-8")
