# Football Data Scraper

Este repositorio contiene un pipeline en PySpark para descargar los CSV de
[football-data.co.uk](https://www.football-data.co.uk), guardarlos en la capa
bronze y construir capas `silver` y `gold` con datos normalizados y agregados.

## Arquitectura del código

El código está organizado por capas dentro del paquete `football_data`:

- `football_data.bronze`: descarga CSV temporales por corrida y materializa una
  copia persistente en Parquet.
- `football_data.silver`: transforma los CSV raw en una tabla normalizada de
  partidos.
- `football_data.gold`: genera agregados curados por equipo, liga y temporada,
  incluyendo métricas avanzadas de rendimiento, volumen ofensivo y disciplina.
- `football_data.utils`: helpers de configuración, temporadas y rutas.
- `football_data_scraper.run_scraper`: entrypoint que ejecuta el pipeline
  `Bronze -> Silver -> Gold`.

Funciones principales:

- `football_data.utils.config.load_config_from_env`
- `football_data.utils.seasons.build_season_list`
- `football_data.bronze.run_spark_job`
- `football_data.silver.run_silver_layer`
- `football_data.gold.run_gold_layer`

## Despliegue en Local

Para desarrollo o pruebas locales:

1. **Requisitos**: Docker, Docker Compose.

2. **Levantar servicios**: Ejecuta `docker-compose up -d` para iniciar Airflow y Postgres.

3. **Acceder a Airflow**: Ve a http://localhost:8080 (usuario: airflow, contraseña: airflow).

4. **Configurar variables**: En Airflow UI > Admin > Variables, agrega las necesarias (FOOTBALL_DATA_*).

5. **Ejecutar DAG**: Activa `football_data_pipeline_local` y ejecuta. Procesa datos localmente con PySpark.

Nota: Para ML, ajusta `run_ml.py` para usar datos locales en lugar de BigQuery.

## Despliegue en Google Cloud Platform (GCP)

### Requisitos previos
- Proyecto GCP con APIs habilitadas: Dataproc, BigQuery, Cloud Storage, Cloud Composer.
- Bucket GCS para almacenamiento de datos y scripts.
- Cluster Dataproc creado.
- Dataset en BigQuery.

### Variables de entorno
Configurar en Cloud Composer:
- `GCP_PROJECT`: ID del proyecto GCP.
- `GCP_REGION`: Región (ej. us-central1).
- `DATAPROC_CLUSTER`: Nombre del cluster Dataproc.
- `BQ_DATASET`: Nombre del dataset en BigQuery.
- `GCS_BUCKET`: Nombre del bucket GCS.
- `FOOTBALL_DATA_PROJECT_DIR`: /opt/airflow/project (para Composer).

### Pasos de despliegue
1. Subir el código a GCS: `gs://<bucket>/football_data/` (todo el paquete football_data con scripts en sus carpetas).
2. Subir el paquete football_data a GCS o instalar en el cluster.
3. Crear el DAG en Cloud Composer.
4. Ejecutar el DAG: las tablas en BigQuery se crean automáticamente solo la primera vez (si no existen), optimizando costos. El pipeline procesa datos diariamente a las 2 AM y entrena un modelo de ML básico para predicciones de resultados de partidos.

Las tablas en BigQuery estarán disponibles para ML y análisis.
  raw/
    football-data/
      _runs/
        20260411T120000Z/
          england_premier_league/
            9394.csv
            ...
    bronze/
      matches/
        league_code=E0/
          season=2324/
            part-*.parquet
    silver/
      matches/
        league_code=E0/
          season=2324/
            part-*.parquet
    gold/
      team_season_table/
        league_code=E0/
          season=2324/
            part-*.parquet
      league_season_summary/
        league_code=E0/
          season=2324/
            part-*.parquet
```

Por defecto, cada ejecución descarga primero CSV temporales en
`data/raw/football-data/_runs/<run_id>/...`, luego materializa la capa bronze en
Parquet en `data/raw/bronze/matches` y finalmente elimina esos CSV temporales
si la corrida termina bien. Puedes cambiar la raíz temporal con
`FOOTBALL_DATA_OUTPUT_DIR`.

## Variables de configuración

- `FOOTBALL_DATA_OUTPUT_DIR`: carpeta base para el staging temporal de CSV. Por
  defecto: `data/raw/football-data`.
- `FOOTBALL_DATA_START_YEAR`: primer año histórico a descargar. Por defecto:
  `1993`.
- `FOOTBALL_DATA_PARTITIONS`: número de particiones Spark. Por defecto: `24`.
- `FOOTBALL_DATA_GCS_BUCKET`: bucket de Cloud Storage para copiar los archivos.
- `FOOTBALL_DATA_GCS_PREFIX`: prefijo dentro del bucket. Por defecto:
  `lakehouse/football-data`.
- `FOOTBALL_DATA_LEAGUE_CODES`: ligas personalizadas en formato
  `CODIGO=nombre_largo,CODIGO2=otra_liga`.

## Requisitos

- Python 3.10+
- PySpark 3.5
- Java Runtime
- Credenciales de Google Cloud si se usará subida a GCS

## Instalación rápida

```bash
python -m venv .venv
source .venv/bin/activate  # En Windows usa .venv\Scripts\activate
pip install -r requirements.txt
```

## Ejecución local

```bash
spark-submit football_data_scraper.py
```

El pipeline ejecuta en orden:

1. Descarga de CSV temporales por ejecución.
2. Materialización de `bronze/matches` en Parquet.
3. Construcción de `silver/matches`.
4. Construcción de `gold/team_season_table`.
5. Construcción de `gold/league_season_summary`.

La capa `gold` ahora añade, entre otras, estas métricas avanzadas:

- En `team_season_table`: `points_per_match`, `win_rate`,
  `goals_for_per_match`, `clean_sheet_rate`, `both_teams_scored_rate`,
  `over_2_5_rate`, `avg_shots_for`, `avg_shots_on_target_for`,
  `shot_accuracy`, `shot_conversion_rate`, `shot_dominance_index`,
  `on_target_dominance_index`, `territorial_dominance_proxy`,
  `net_efficiency`, `pressure_without_payoff`, `opponent_suppression_rate`,
  `fast_start_rate`, `second_half_surge_index`,
  `second_half_collapse_index`, `comeback_rate`, `blown_lead_rate`,
  `first_half_control_index`, `avg_corners_for` y métricas de disciplina por
  partido.
- En `league_season_summary`: `home_win_rate`, `away_win_rate`,
  `both_teams_scored_rate`, `over_1_5_rate`, `over_2_5_rate`,
  `avg_shots_per_match`, `avg_shots_on_target_per_match`,
  `avg_corners_per_match` y tarjetas medias por partido.

## Verificación rápida

```bash
python -m compileall football_data_scraper.py football_data/
```

Luego revisa que existan archivos en:

- `data/raw/bronze/matches`
- `data/raw/silver/matches`
- `data/raw/gold/team_season_table`
- `data/raw/gold/league_season_summary`

## Predicción de la siguiente jornada

El módulo de ML entrena con métricas previas al partido: forma del local,
forma del visitante, goles, tiros y diferencias entre ambos equipos. Esto
permite predecir partidos pendientes sin usar datos que solo existen después
del encuentro.

Entrena o actualiza el modelo:

```bash
python -m football_data.ml.run_ml train
```

Genera las predicciones de la siguiente jornada pendiente:

```bash
python -m football_data.ml.run_ml predict-next-round
```

También puedes filtrar una liga/temporada y controlar la ventana de la jornada:

```bash
python -m football_data.ml.run_ml predict-next-round --league-code SP1 --season 2526 --round-days 7
```

La salida se imprime en consola y se guarda en:

```text
models/next_round_predictions.csv
```

## Carga automática a GCS

Si defines `FOOTBALL_DATA_GCS_BUCKET`, cada descarga exitosa se sube a Cloud
Storage respetando la misma estructura de carpetas. Ejemplo:

```bash
export FOOTBALL_DATA_GCS_BUCKET="mi-bucket-lakehouse"
export FOOTBALL_DATA_GCS_PREFIX="lakehouse/football-data"
spark-submit football_data_scraper.py
```

## Despliegue con Docker y Airflow

El repositorio incluye un despliegue local con Docker Compose para ejecutar el
pipeline desde Airflow. La imagen de Airflow instala Java y las dependencias de
`requirements.txt`, de modo que las tareas pueden levantar Spark en modo local.

Servicios incluidos:

- `postgres`: base de metadatos de Airflow.
- `airflow-webserver`: UI de Airflow en `http://localhost:8080`.
- `airflow-scheduler`: planificador que ejecuta el DAG.
- `airflow-init`: inicializa la base de datos y crea el usuario admin.

Arranque inicial:

```bash
docker compose up airflow-init
docker compose up -d
```

Credenciales por defecto de Airflow:

- Usuario: `airflow`
- Password: `airflow`

El DAG se llama `football_data_pipeline` y ejecuta las capas en este orden:

1. `bronze_download_matches`
2. `silver_normalize_matches`
3. `gold_build_aggregates`

El volumen del proyecto se monta en `/opt/airflow/project`, y la salida queda
en:

```text
data/raw/bronze/matches
data/raw/silver/matches
data/raw/gold/team_season_table
data/raw/gold/league_season_summary
```

Puedes ajustar la corrida con variables de entorno antes de iniciar Compose:

```bash
export FOOTBALL_DATA_START_YEAR=2020
export FOOTBALL_DATA_PARTITIONS=4
export FOOTBALL_DATA_LEAGUE_CODES="E0=england_premier_league,SP1=spain_la_liga"
docker compose up -d --build
```

En PowerShell:

```powershell
$env:FOOTBALL_DATA_START_YEAR = "2020"
$env:FOOTBALL_DATA_PARTITIONS = "4"
$env:FOOTBALL_DATA_LEAGUE_CODES = "E0=england_premier_league,SP1=spain_la_liga"
docker compose up -d --build
```

## Programación diaria

Puedes programar `football_data_scraper.py` en Dataproc Serverless u otro
orquestador similar para ejecutar el pipeline completo todos los días. Cada
ejecución sobrescribe las capas generadas, así que el proceso es reproducible.
