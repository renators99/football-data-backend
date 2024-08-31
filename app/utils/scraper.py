import pandas as pd
import requests
from io import StringIO

def scrape_football_data(leagues: list, seasons: list) -> pd.DataFrame:
    # Define los nombres de las columnas esperadas
    expected_columns = [
        'Div', 'Date', 'HomeTeam', 'AwayTeam', 'FTHG', 'FTAG', 'FTR', 'HTHG', 'HTAG',
        'HTR', 'HS', 'AS', 'HST', 'AST', 'HC', 'AC', 
        'HF', 'AF', 'HO', 'AO', 'HY', 'AY', 'HR', 'AR', 
        'GBA', 'GBH', 'GBD', 'IWH', 'IWD', 'IWA', 
        'LBH', 'LBD', 'LBA', 'SOH', 'SOD', 'SOA', 
        'SBH', 'SBD', 'SBA', 'WHH', 'WHD', 'WHA'
    ]
    
    all_data = []
    
    for season in seasons:
        for league in leagues:
            print(f"Descargando datos para {season} en la liga {league}...")
            base_url = f"https://www.football-data.co.uk/mmz4281/{season}/{league}.csv"
            response = requests.get(base_url)
            
            if response.status_code == 200:
                csv_data = StringIO(response.text)
                try:
                    # Leer el CSV con el encabezado real del archivo
                    df = pd.read_csv(csv_data, engine='python')
                    
                    # Filtrar solo las columnas que existen en el DataFrame y están en la lista esperada
                    available_columns = [col for col in df.columns if col in expected_columns]
                    filtered_df = df[available_columns]
                    
                    # Eliminar filas con valores nulos en las columnas clave
                    filtered_df.dropna(subset=['HomeTeam', 'AwayTeam', 'FTHG', 'FTAG'], inplace=True)
                    
                    # Añadir los datos procesados a la lista
                    all_data.append(filtered_df)
                
                except Exception as e:
                    print(f"Error al procesar los datos del CSV para {league} en la temporada {season}: {e}")
            elif response.status_code == 404:
                print(f"Datos no encontrados para {league} en la temporada {season}. URL: {base_url}")
            else:
                print(f"Error al descargar los datos: {response.status_code}")
    
    # Concatenar todos los DataFrames si hay datos disponibles
    if all_data:
        df_final = pd.concat(all_data, ignore_index=True)
        return df_final
    else:
        return pd.DataFrame() 