"""Script to train a simple ML model for predicting match results (local and BigQuery versions)."""

import logging
import os
from pathlib import Path

import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
import joblib

from ..utils.config import load_config_from_env
from ..utils.layers import silver_root

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)

# Imports condicionales para GCP (solo si es necesario)
try:
    from google.cloud import bigquery
    from google.cloud import storage
    GCP_AVAILABLE = True
except ImportError:
    GCP_AVAILABLE = False
    LOGGER.warning("Google Cloud libraries not available. Running in local mode only.")

def _load_data_local(config):
    """Load data from the local silver parquet dataset."""
    data_path = silver_root(Path(config["output_dir"]).parent) / "matches"
    if not data_path.exists():
        raise FileNotFoundError(f"El archivo de datos no existe: {data_path}. Ejecuta el pipeline hasta la capa silver para generarlo.")
    
    df = pd.read_parquet(data_path)
    if 'season_start_year' in df.columns:
        df = df[df['season_start_year'] >= 2020]
    if 'result' not in df.columns and 'full_time_result' in df.columns:
        df['result'] = df['full_time_result'].map({'H': 1, 'A': 2, 'D': 0})
    return df.dropna()

def _load_data_bigquery(config):
    """Load data from BigQuery."""
    if not GCP_AVAILABLE:
        raise RuntimeError("BigQuery not available. Install google-cloud-bigquery or run in local mode.")
    
    bq_client = bigquery.Client()
    dataset = config.get("bq_dataset", "football_data")
    query = f"""
    SELECT
        home_team, away_team, full_time_home_goals, full_time_away_goals,
        half_time_home_goals, half_time_away_goals, home_shots, away_shots,
        CASE WHEN full_time_result = 'H' THEN 1 WHEN full_time_result = 'A' THEN 2 ELSE 0 END as result
    FROM `{config['gcp_project']}.{dataset}.silver_matches`
    WHERE season_start_year >= 2020
    """
    return bq_client.query(query).to_dataframe().dropna()

def _save_model_local(model):
    """Save model locally."""
    models_dir = Path("models")
    models_dir.mkdir(exist_ok=True)
    model_path = models_dir / "football_match_predictor.pkl"
    joblib.dump(model, model_path)
    LOGGER.info(f"Model saved locally to {model_path}")

def _save_model_gcs(model, config):
    """Save model to GCS."""
    if not GCP_AVAILABLE:
        raise RuntimeError("GCS not available. Install google-cloud-storage or run in local mode.")
    
    storage_client = storage.Client()
    bucket = storage_client.bucket(config['gcs_bucket'])
    blob = bucket.blob('models/football_match_predictor.pkl')
    blob.upload_from_string(joblib.dumps(model), content_type='application/octet-stream')
    LOGGER.info("Model saved to GCS")

def train_model():
    """Train a model to predict match outcomes."""
    config = load_config_from_env()
    
    # Detectar entorno: si GCP_PROJECT existe, usar BigQuery; sino, local
    is_gcp = bool(os.getenv("GCP_PROJECT"))
    if is_gcp:
        if not GCP_AVAILABLE:
            raise RuntimeError("GCP mode selected but libraries not installed.")
        config["gcp_project"] = os.getenv("GCP_PROJECT")
        config["gcs_bucket"] = os.getenv("GCS_BUCKET", "football-data-models")  # Valor por defecto
        config["bq_dataset"] = os.getenv("BQ_DATASET", "football_data")
        df = _load_data_bigquery(config)
    else:
        df = _load_data_local(config)
    
    features = ['full_time_home_goals', 'full_time_away_goals', 'half_time_home_goals', 'half_time_away_goals', 'home_shots', 'away_shots']
    X = df[features]
    y = df['result']
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)
    
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    LOGGER.info(f"Model accuracy: {accuracy:.2f}")
    
    # Guardar modelo según el entorno
    if is_gcp:
        _save_model_gcs(model, config)
    else:
        _save_model_local(model)

if __name__ == "__main__":
    train_model()
