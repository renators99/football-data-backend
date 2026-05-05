"""Train and run match-result predictions.

The model uses only pre-match information so it can score pending fixtures.
Labels are encoded as: draw=0, home win=1, away win=2.
"""

import argparse
import logging
import os
from datetime import date
from pathlib import Path
from typing import Iterable, Mapping, Optional

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

from ..utils.config import load_config_from_env
from ..utils.layers import silver_root

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)

try:
    from google.cloud import bigquery
    from google.cloud import storage

    GCP_AVAILABLE = True
except ImportError:
    GCP_AVAILABLE = False
    LOGGER.warning("Google Cloud libraries not available. Running in local mode only.")


MODEL_PATH = Path("models") / "football_match_predictor.pkl"
PREDICTIONS_PATH = Path("models") / "next_round_predictions.csv"
RESULT_TO_LABEL = {"D": 0, "H": 1, "A": 2}
LABEL_TO_RESULT = {
    0: "Empate",
    1: "Victoria local",
    2: "Victoria visitante",
}
PROBABILITY_COLUMNS = {
    0: "prob_empate",
    1: "prob_victoria_local",
    2: "prob_victoria_visitante",
}
BASE_TEAM_METRICS = [
    "matches_played",
    "points_per_match",
    "win_rate",
    "draw_rate",
    "loss_rate",
    "goals_for_per_match",
    "goals_against_per_match",
    "goal_difference_per_match",
    "shots_for_per_match",
    "shots_against_per_match",
    "shots_on_target_for_per_match",
    "shots_on_target_against_per_match",
]
FEATURE_COLUMNS = [
    *(f"home_{metric}" for metric in BASE_TEAM_METRICS),
    *(f"away_{metric}" for metric in BASE_TEAM_METRICS),
    "points_per_match_diff",
    "win_rate_diff",
    "draw_rate_diff",
    "goals_for_per_match_diff",
    "goals_against_per_match_diff",
    "goal_difference_per_match_diff",
    "shots_for_per_match_diff",
    "shots_on_target_for_per_match_diff",
]


def _load_data_local(config: Mapping[str, object]) -> pd.DataFrame:
    """Load data from the local silver parquet dataset."""

    data_path = silver_root(Path(config["output_dir"]).parent) / "matches"
    if not data_path.exists():
        raise FileNotFoundError(
            f"No existe la tabla silver en {data_path}. Ejecuta el pipeline hasta silver."
        )

    parquet_files = [
        path
        for path in data_path.rglob("*.parquet")
        if not any(part.startswith("_") for part in path.relative_to(data_path).parts)
    ]
    if not parquet_files:
        raise FileNotFoundError(
            f"No hay archivos Parquet finales en {data_path}. "
            "La capa silver parece incompleta; vuelve a ejecutar silver o el pipeline completo."
        )

    df = pd.read_parquet(parquet_files)
    return _normalize_matches(df)


def _load_data_bigquery(config: Mapping[str, object]) -> pd.DataFrame:
    """Load data from BigQuery."""

    if not GCP_AVAILABLE:
        raise RuntimeError("BigQuery no disponible. Instala google-cloud-bigquery o usa modo local.")

    bq_client = bigquery.Client()
    dataset = config.get("bq_dataset", "football_data")
    query = f"""
    SELECT
        league_code, season, season_start_year, match_date, home_team, away_team,
        full_time_home_goals, full_time_away_goals, half_time_home_goals,
        half_time_away_goals, full_time_result, home_shots, away_shots,
        home_shots_on_target, away_shots_on_target
    FROM `{config['gcp_project']}.{dataset}.silver_matches`
    WHERE season_start_year >= 2020
    """
    return _normalize_matches(bq_client.query(query).to_dataframe())


def _normalize_matches(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["match_date"] = pd.to_datetime(df["match_date"], errors="coerce")
    df["season_start_year"] = _season_start_year(df["season"])
    df = df[df["season_start_year"] >= 2020]
    if "full_time_result" not in df.columns and "result" in df.columns:
        reverse = {value: key for key, value in RESULT_TO_LABEL.items()}
        df["full_time_result"] = df["result"].map(reverse)
    df["result"] = df["full_time_result"].map(RESULT_TO_LABEL)
    return df


def _season_start_year(season: pd.Series) -> pd.Series:
    season_prefix = season.astype(str).str.zfill(4).str[:2]
    start_year = pd.to_numeric(season_prefix, errors="coerce")
    return start_year.where(start_year >= 80, start_year + 100) + 1900


def _load_matches(config: Mapping[str, object], *, is_gcp: bool) -> pd.DataFrame:
    if is_gcp:
        return _load_data_bigquery(config)
    return _load_data_local(config)


def _completed_matches(df: pd.DataFrame) -> pd.DataFrame:
    return df[df["full_time_result"].isin(RESULT_TO_LABEL)].dropna(
        subset=["match_date", "home_team", "away_team", "result"]
    )


def _optional_numeric(frame: pd.DataFrame, column: str) -> pd.Series:
    if column in frame.columns:
        return pd.to_numeric(frame[column], errors="coerce").fillna(0)
    return pd.Series(0, index=frame.index)


def _team_match_rows(matches: pd.DataFrame) -> pd.DataFrame:
    matches = matches.copy()
    home_goals = _optional_numeric(matches, "full_time_home_goals")
    away_goals = _optional_numeric(matches, "full_time_away_goals")
    home_shots = _optional_numeric(matches, "home_shots")
    away_shots = _optional_numeric(matches, "away_shots")
    home_sot = _optional_numeric(matches, "home_shots_on_target")
    away_sot = _optional_numeric(matches, "away_shots_on_target")

    common = matches[["league_code", "season", "match_date"]].copy()
    common["match_id"] = matches.index

    home = common.assign(
        team=matches["home_team"].values,
        venue="home",
        points=matches["full_time_result"].map({"H": 3, "D": 1, "A": 0}).values,
        win=(matches["full_time_result"] == "H").astype(int).values,
        draw=(matches["full_time_result"] == "D").astype(int).values,
        loss=(matches["full_time_result"] == "A").astype(int).values,
        goals_for=home_goals.values,
        goals_against=away_goals.values,
        shots_for=home_shots.values,
        shots_against=away_shots.values,
        shots_on_target_for=home_sot.values,
        shots_on_target_against=away_sot.values,
    )
    away = common.assign(
        team=matches["away_team"].values,
        venue="away",
        points=matches["full_time_result"].map({"A": 3, "D": 1, "H": 0}).values,
        win=(matches["full_time_result"] == "A").astype(int).values,
        draw=(matches["full_time_result"] == "D").astype(int).values,
        loss=(matches["full_time_result"] == "H").astype(int).values,
        goals_for=away_goals.values,
        goals_against=home_goals.values,
        shots_for=away_shots.values,
        shots_against=home_shots.values,
        shots_on_target_for=away_sot.values,
        shots_on_target_against=home_sot.values,
    )
    return pd.concat([home, away], ignore_index=True).sort_values(
        ["league_code", "season", "team", "match_date", "match_id"]
    )


def _add_running_team_stats(team_rows: pd.DataFrame) -> pd.DataFrame:
    value_columns = [
        "points",
        "win",
        "draw",
        "loss",
        "goals_for",
        "goals_against",
        "shots_for",
        "shots_against",
        "shots_on_target_for",
        "shots_on_target_against",
    ]
    group_keys = ["league_code", "season", "team"]
    grouped = team_rows.groupby(group_keys, sort=False, observed=False)
    previous = (
        grouped[value_columns]
        .cumsum()
        .groupby([team_rows[key] for key in group_keys], observed=False)
        .shift()
    )
    stats = team_rows[["match_id", "venue"]].copy()
    stats["matches_played"] = grouped.cumcount()

    for column in value_columns:
        stats[f"sum_{column}"] = previous[column].fillna(0)

    stats = _derive_rates(stats)
    return stats


def _derive_rates(stats: pd.DataFrame) -> pd.DataFrame:
    matches = stats["matches_played"].astype("float").where(stats["matches_played"] != 0)
    stats["points_per_match"] = stats["sum_points"] / matches
    stats["win_rate"] = stats["sum_win"] / matches
    stats["draw_rate"] = stats["sum_draw"] / matches
    stats["loss_rate"] = stats["sum_loss"] / matches
    stats["goals_for_per_match"] = stats["sum_goals_for"] / matches
    stats["goals_against_per_match"] = stats["sum_goals_against"] / matches
    stats["goal_difference_per_match"] = (
        stats["sum_goals_for"] - stats["sum_goals_against"]
    ) / matches
    stats["shots_for_per_match"] = stats["sum_shots_for"] / matches
    stats["shots_against_per_match"] = stats["sum_shots_against"] / matches
    stats["shots_on_target_for_per_match"] = stats["sum_shots_on_target_for"] / matches
    stats["shots_on_target_against_per_match"] = (
        stats["sum_shots_on_target_against"] / matches
    )
    return stats[["match_id", "venue", *BASE_TEAM_METRICS]]


def _build_training_frame(matches: pd.DataFrame) -> pd.DataFrame:
    completed = _completed_matches(matches).sort_values(["match_date", "league_code", "season"])
    team_rows = _team_match_rows(completed)
    stats = _add_running_team_stats(team_rows)

    home_stats = stats[stats["venue"] == "home"].drop(columns=["venue"]).add_prefix("home_")
    away_stats = stats[stats["venue"] == "away"].drop(columns=["venue"]).add_prefix("away_")

    features = completed.copy()
    features["home_match_id"] = features.index
    features["away_match_id"] = features.index
    features = features.merge(home_stats, on="home_match_id", how="left")
    features = features.merge(away_stats, on="away_match_id", how="left")
    features = _add_diff_features(features)

    return features.dropna(subset=["result"])


def _add_diff_features(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy()
    for metric in [
        "points_per_match",
        "win_rate",
        "draw_rate",
        "goals_for_per_match",
        "goals_against_per_match",
        "goal_difference_per_match",
        "shots_for_per_match",
        "shots_on_target_for_per_match",
    ]:
        frame[f"{metric}_diff"] = frame[f"home_{metric}"] - frame[f"away_{metric}"]
    return frame


def _model_bundle(model: Pipeline) -> dict:
    return {
        "model": model,
        "feature_columns": FEATURE_COLUMNS,
        "label_to_result": LABEL_TO_RESULT,
    }


def _save_model_local(model: Pipeline) -> Path:
    MODEL_PATH.parent.mkdir(exist_ok=True)
    joblib.dump(_model_bundle(model), MODEL_PATH)
    LOGGER.info("Model saved locally to %s", MODEL_PATH)
    return MODEL_PATH


def _save_model_gcs(model: Pipeline, config: Mapping[str, object]) -> None:
    if not GCP_AVAILABLE:
        raise RuntimeError("GCS no disponible. Instala google-cloud-storage o usa modo local.")

    storage_client = storage.Client()
    bucket = storage_client.bucket(config["gcs_bucket"])
    blob = bucket.blob("models/football_match_predictor.pkl")
    blob.upload_from_string(joblib.dumps(_model_bundle(model)), content_type="application/octet-stream")
    LOGGER.info("Model saved to GCS")


def train_model() -> Pipeline:
    """Train a model to predict match outcomes."""

    config = load_config_from_env()
    is_gcp = bool(os.getenv("GCP_PROJECT"))
    if is_gcp:
        if not GCP_AVAILABLE:
            raise RuntimeError("GCP mode selected but libraries are not installed.")
        config["gcp_project"] = os.getenv("GCP_PROJECT")
        config["gcs_bucket"] = os.getenv("GCS_BUCKET", "football-data-models")
        config["bq_dataset"] = os.getenv("BQ_DATASET", "football_data")

    matches = _load_matches(config, is_gcp=is_gcp)
    training = _build_training_frame(matches)
    training = training[training["home_matches_played"].fillna(0) > 0]
    training = training[training["away_matches_played"].fillna(0) > 0]

    X = training[FEATURE_COLUMNS]
    y = training["result"].astype(int)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    model = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="constant", fill_value=0)),
            ("classifier", RandomForestClassifier(n_estimators=300, random_state=42, class_weight="balanced")),
        ]
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    LOGGER.info("Model accuracy: %.2f", accuracy)

    if is_gcp:
        _save_model_gcs(model, config)
    else:
        _save_model_local(model)
    return model


def _load_model(path: Path = MODEL_PATH) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"No existe el modelo {path}. Ejecuta primero: python -m football_data.ml.run_ml train")
    bundle = joblib.load(path)
    if isinstance(bundle, dict) and "model" in bundle:
        return bundle
    return _model_bundle(bundle)


def _pending_matches(
    matches: pd.DataFrame,
    *,
    as_of: date,
    round_days: int,
    league_code: Optional[str],
    season: Optional[str],
) -> pd.DataFrame:
    pending = matches[~matches["full_time_result"].isin(RESULT_TO_LABEL)].dropna(
        subset=["match_date", "home_team", "away_team"]
    )
    if league_code:
        pending = pending[pending["league_code"] == league_code]
    if season:
        pending = pending[pending["season"].astype(str) == str(season)]

    pending = pending[pending["match_date"].dt.date >= as_of]
    if pending.empty:
        return pending

    windows = []
    for _, group in pending.groupby(["league_code", "season"], dropna=False, observed=False):
        start = group["match_date"].min()
        end = start + pd.Timedelta(days=round_days)
        windows.append(group[(group["match_date"] >= start) & (group["match_date"] < end)])
    return pd.concat(windows, ignore_index=False).sort_values(["match_date", "league_code", "home_team"])


def _team_snapshot(team_rows: pd.DataFrame, fixture: pd.Series, team: str) -> pd.Series:
    history = team_rows[
        (team_rows["league_code"] == fixture["league_code"])
        & (team_rows["season"] == fixture["season"])
        & (team_rows["team"] == team)
        & (team_rows["match_date"] < fixture["match_date"])
    ]
    if history.empty:
        history = team_rows[
            (team_rows["league_code"] == fixture["league_code"])
            & (team_rows["team"] == team)
            & (team_rows["match_date"] < fixture["match_date"])
        ]

    sums = {
        "matches_played": len(history),
        "sum_points": history["points"].sum(),
        "sum_win": history["win"].sum(),
        "sum_draw": history["draw"].sum(),
        "sum_loss": history["loss"].sum(),
        "sum_goals_for": history["goals_for"].sum(),
        "sum_goals_against": history["goals_against"].sum(),
        "sum_shots_for": history["shots_for"].sum(),
        "sum_shots_against": history["shots_against"].sum(),
        "sum_shots_on_target_for": history["shots_on_target_for"].sum(),
        "sum_shots_on_target_against": history["shots_on_target_against"].sum(),
    }
    return _derive_rates(pd.DataFrame([{"match_id": 0, "venue": "snapshot", **sums}])).iloc[0]


def _build_prediction_frame(matches: pd.DataFrame, fixtures: pd.DataFrame) -> pd.DataFrame:
    team_rows = _team_match_rows(_completed_matches(matches))
    rows = []
    for _, fixture in fixtures.iterrows():
        row = fixture.copy()
        home_stats = _team_snapshot(team_rows, fixture, fixture["home_team"])
        away_stats = _team_snapshot(team_rows, fixture, fixture["away_team"])
        for metric in BASE_TEAM_METRICS:
            row[f"home_{metric}"] = home_stats[metric]
            row[f"away_{metric}"] = away_stats[metric]
        rows.append(row)
    return _add_diff_features(pd.DataFrame(rows))


def _probability_frame(model: Pipeline, X: pd.DataFrame) -> pd.DataFrame:
    probabilities = model.predict_proba(X)
    frame = pd.DataFrame(index=X.index)
    for class_label, probability in zip(model.classes_, probabilities.T):
        frame[PROBABILITY_COLUMNS[int(class_label)]] = probability
    for column in PROBABILITY_COLUMNS.values():
        if column not in frame:
            frame[column] = 0.0
    return frame


def predict_next_round(
    *,
    as_of: Optional[date] = None,
    round_days: int = 7,
    league_code: Optional[str] = None,
    season: Optional[str] = None,
    model_path: Path = MODEL_PATH,
    output_path: Path = PREDICTIONS_PATH,
) -> pd.DataFrame:
    """Predict the pending fixtures in the next round/window."""

    config = load_config_from_env()
    matches = _load_matches(config, is_gcp=False)
    as_of = as_of or date.today()
    fixtures = _pending_matches(
        matches,
        as_of=as_of,
        round_days=round_days,
        league_code=league_code,
        season=season,
    )
    if fixtures.empty:
        LOGGER.warning("No hay partidos pendientes desde %s con los filtros indicados.", as_of)
        return fixtures

    bundle = _load_model(model_path)
    model = bundle["model"]
    feature_columns: Iterable[str] = bundle.get("feature_columns", FEATURE_COLUMNS)
    prediction_frame = _build_prediction_frame(matches, fixtures)
    X = prediction_frame[list(feature_columns)]
    labels = model.predict(X).astype(int)
    probabilities = _probability_frame(model, X)

    output = prediction_frame[
        ["league_code", "season", "match_date", "home_team", "away_team"]
    ].copy()
    output["prediccion"] = [LABEL_TO_RESULT[label] for label in labels]
    output = pd.concat([output, probabilities], axis=1)
    output["confianza"] = probabilities.max(axis=1)

    output_path.parent.mkdir(exist_ok=True)
    output.to_csv(output_path, index=False)
    LOGGER.info("Predicciones guardadas en %s", output_path)
    return output


def _parse_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    return date.fromisoformat(value)


def _print_predictions(predictions: pd.DataFrame) -> None:
    if predictions.empty:
        print("No hay partidos pendientes para predecir.")
        return
    printable = predictions.copy()
    printable["match_date"] = pd.to_datetime(printable["match_date"]).dt.date
    for column in ["prob_victoria_local", "prob_empate", "prob_victoria_visitante", "confianza"]:
        printable[column] = (printable[column] * 100).round(1).astype(str) + "%"
    print(printable.to_string(index=False))


def main() -> None:
    parser = argparse.ArgumentParser(description="Train and run football match predictions.")
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("train", help="Entrena el modelo con datos silver.")

    predict_parser = subparsers.add_parser(
        "predict-next-round",
        help="Predice la siguiente jornada de partidos pendientes.",
    )
    predict_parser.add_argument("--as-of", help="Fecha base YYYY-MM-DD. Por defecto, hoy.")
    predict_parser.add_argument("--round-days", type=int, default=7, help="Ventana de días de la jornada.")
    predict_parser.add_argument("--league-code", help="Filtrar liga, por ejemplo E0 o SP1.")
    predict_parser.add_argument("--season", help="Filtrar temporada, por ejemplo 2526.")
    predict_parser.add_argument("--model-path", type=Path, default=MODEL_PATH)
    predict_parser.add_argument("--output-path", type=Path, default=PREDICTIONS_PATH)

    args = parser.parse_args()
    command = args.command or "train"
    if command == "train":
        train_model()
        return

    predictions = predict_next_round(
        as_of=_parse_date(args.as_of),
        round_days=args.round_days,
        league_code=args.league_code,
        season=args.season,
        model_path=args.model_path,
        output_path=args.output_path,
    )
    _print_predictions(predictions)


if __name__ == "__main__":
    main()
