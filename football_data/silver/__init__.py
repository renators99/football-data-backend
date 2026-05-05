"""Build the silver layer with normalized match-level rows."""

import logging
from pathlib import Path
from typing import Mapping

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F

from ..utils.layers import bronze_matches_root, silver_root

LOGGER = logging.getLogger(__name__)


def _optional_integer_column(frame: DataFrame, column_name: str):
    if column_name in frame.columns:
        return F.col(column_name).cast("int")
    return F.lit(None).cast("int")


def _parse_match_date():
    date_text = F.trim(F.col("Date"))
    return F.coalesce(
        F.when(date_text.rlike(r"^\d{1,2}/\d{1,2}/\d{4}$"), F.to_date(date_text, "d/M/yyyy")),
        F.when(date_text.rlike(r"^\d{1,2}/\d{1,2}/\d{2}$"), F.to_date(date_text, "d/M/yy")),
        F.when(date_text.rlike(r"^\d{4}-\d{1,2}-\d{1,2}$"), F.to_date(date_text, "yyyy-M-d")),
    )


def build_silver_matches(
    bronze_matches: DataFrame,
) -> DataFrame:
    half_time_home_goals = _optional_integer_column(bronze_matches, "HTHG")
    half_time_away_goals = _optional_integer_column(bronze_matches, "HTAG")
    home_shots = _optional_integer_column(bronze_matches, "HS")
    away_shots = _optional_integer_column(bronze_matches, "AS")
    home_shots_on_target = _optional_integer_column(bronze_matches, "HST")
    away_shots_on_target = _optional_integer_column(bronze_matches, "AST")
    home_corners = _optional_integer_column(bronze_matches, "HC")
    away_corners = _optional_integer_column(bronze_matches, "AC")
    home_fouls = _optional_integer_column(bronze_matches, "HF")
    away_fouls = _optional_integer_column(bronze_matches, "AF")
    home_yellow_cards = _optional_integer_column(bronze_matches, "HY")
    away_yellow_cards = _optional_integer_column(bronze_matches, "AY")
    home_red_cards = _optional_integer_column(bronze_matches, "HR")
    away_red_cards = _optional_integer_column(bronze_matches, "AR")

    return (
        bronze_matches.withColumn("match_date", _parse_match_date())
        .withColumn("home_team", F.col("HomeTeam"))
        .withColumn("away_team", F.col("AwayTeam"))
        .withColumn("full_time_home_goals", F.coalesce(F.col("FTHG").cast("int"), F.lit(0)))
        .withColumn("full_time_away_goals", F.coalesce(F.col("FTAG").cast("int"), F.lit(0)))
        .withColumn("half_time_home_goals", half_time_home_goals)
        .withColumn("half_time_away_goals", half_time_away_goals)
        .withColumn("full_time_result", F.coalesce(F.col("FTR"), F.lit("U")))
        .withColumn("home_shots", home_shots)
        .withColumn("away_shots", away_shots)
        .withColumn("home_shots_on_target", home_shots_on_target)
        .withColumn("away_shots_on_target", away_shots_on_target)
        .withColumn("home_corners", home_corners)
        .withColumn("away_corners", away_corners)
        .withColumn("home_fouls", home_fouls)
        .withColumn("away_fouls", away_fouls)
        .withColumn("home_yellow_cards", home_yellow_cards)
        .withColumn("away_yellow_cards", away_yellow_cards)
        .withColumn("home_red_cards", home_red_cards)
        .withColumn("away_red_cards", away_red_cards)
        .withColumn("season_start_year", (F.substring("season", 1, 2).cast("int") + F.lit(2000)))
        .select(
            "league_code",
            "season",
            "season_start_year",
            "match_date",
            "home_team",
            "away_team",
            "full_time_home_goals",
            "full_time_away_goals",
            "half_time_home_goals",
            "half_time_away_goals",
            "full_time_result",
            "home_shots",
            "away_shots",
            "home_shots_on_target",
            "away_shots_on_target",
            "home_corners",
            "away_corners",
            "home_fouls",
            "away_fouls",
            "home_yellow_cards",
            "away_yellow_cards",
            "home_red_cards",
            "away_red_cards",
        )
        .where(
            F.col("home_team").isNotNull()
            & F.col("away_team").isNotNull()
            & F.col("league_code").isNotNull()
            & F.col("season").isNotNull()
        )
    )


def write_silver_layer(silver_matches: DataFrame, output_dir: Path) -> Path:
    destination = silver_root(output_dir) / "matches"
    silver_matches.write.mode("overwrite").partitionBy("league_code", "season").parquet(str(destination))
    return destination


def run_silver_layer(config: Mapping[str, object]) -> Path:
    """Read raw CSV files and materialize the silver matches table."""

    raw_root = Path(config["output_dir"])
    bronze_matches_path = bronze_matches_root(raw_root)

    spark = (
        SparkSession.builder.appName("football-data-silver")
        .config("spark.sql.execution.arrow.pyspark.enabled", "true")
        .getOrCreate()
    )

    try:
        bronze_matches = spark.read.parquet(str(bronze_matches_path))
        silver_matches = build_silver_matches(bronze_matches)
        destination = write_silver_layer(silver_matches, raw_root.parent)
        LOGGER.info("Silver layer escrita en %s", destination)
        return destination
    finally:
        spark.stop()
