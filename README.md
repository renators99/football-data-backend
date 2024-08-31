# Football Data Scraper and API

Este proyecto proporciona una API para extraer, procesar y almacenar datos de partidos de fútbol de varias ligas europeas utilizando datos de [football-data.co.uk](https://www.football-data.co.uk). La API está construida con FastAPI y utiliza SQLAlchemy para manejar la base de datos.

## Características

- Scrapeo de datos de fútbol desde diversas ligas y temporadas.
- Almacenamiento de datos en una base de datos relacional.
- Endpoints para crear, leer y consultar datos de partidos.
- Despliegue en Google Cloud Platform (GCP) utilizando Docker y Cloud Build.
- Uso de Google Cloud Secrets para gestionar credenciales de manera segura.

## Tecnologías

- **Backend**: FastAPI
- **Base de datos**: SQLAlchemy con PostgreSQL
- **Scraping**: Requests, Pandas
- **Despliegue**: Docker, Google Cloud Platform (GCP), Cloud Build

## Requisitos

- Python 3.10+
- Docker
- Google Cloud SDK (si vas a desplegar en GCP)
- PostgreSQL (local o en GCP)

## Instalación

1. Clona el repositorio:
   ```bash
   git clone https://github.com/tu_usuario/football-data-scraper.git
   cd football-data-scraper
   ```

2. Crea un entorno virtual e instala las dependencias:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # En Windows, usa venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Configura las variables de entorno:
   - Crea un archivo `.env` en la raíz del proyecto con las siguientes variables:
     ```
     DB_USER=tu_usuario
     DB_PASSWORD=tu_contraseña
     DB_HOST=tu_host
     DB_NAME=tu_nombre_bd
     GOOGLE_CLOUD_PROJECT=tu_project_id_gcp
     ```

## Uso

### Localmente

1. Inicia el servidor de desarrollo:
   ```bash
   uvicorn main:app --reload
   ```

2. Accede a la documentación interactiva de la API en tu navegador:
   ```
   http://127.0.0.1:8000/docs
   ```

### Despliegue en GCP

1. Construye y despliega la imagen Docker utilizando Google Cloud Build:
   ```bash
   gcloud builds submit --tag gcr.io/tu_project_id_gcp/football-data-scraper
   ```

2. Despliega el contenedor en Google Cloud Run:
   ```bash
   gcloud run deploy football-data-scraper \
     --image gcr.io/tu_project_id_gcp/football-data-scraper \
     --platform managed \
     --region us-central1 \
     --allow-unauthenticated
   ```

### Endpoints Disponibles

- `POST /scrape-all-seasons/`: Scrapea y guarda los datos de todas las temporadas y ligas configuradas.
- `POST /matches/`: Crea un nuevo partido en la base de datos.
- `GET /matches/`: Recupera una lista de partidos.
- `GET /matches/{match_id}`: Recupera los detalles de un partido específico por ID.

## Gestión de Secretos con GCP

Este proyecto utiliza Google Cloud Secrets Manager para manejar credenciales sensibles como las de la base de datos. Asegúrate de que las credenciales estén correctamente almacenadas en GCP y configuradas en el proyecto.

## Contribuciones

Las contribuciones son bienvenidas. Por favor, sigue los siguientes pasos:

1. Haz un fork del repositorio.
2. Crea una nueva rama (`git checkout -b feature/nueva_caracteristica`).
3. Realiza tus cambios y haz commit (`git commit -m 'Agrega nueva característica'`).
4. Envía los cambios a la rama (`git push origin feature/nueva_caracteristica`).
5. Abre un Pull Request.

## Licencia

Este proyecto está bajo la Licencia MIT. Consulta el archivo [LICENSE](LICENSE) para más detalles.

