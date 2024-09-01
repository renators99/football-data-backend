from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.schemas.match import Match
from app.models.match import MatchResult
from app.utils.scraper import scrape_football_data
from app.api.dependencies import get_db
from datetime import datetime
import pandas as pd

router = APIRouter()

# Lista de temporadas disponibles
seasons = [
    "9394", "9495", "9596", "9697", "9798", "9899", "9900",
    "0001", "0102", "0203", "0304", "0405", "0506", "0607",
    "0708", "0809", "0910", "1011", "1112", "1213", "1314",
    "1415", "1516", "1617", "1718", "1819", "1920", "2021",
    "2122", "2223", "2324"
]

# Lista de ligas incluyendo Países Bajos y Escocia
leagues = [
    "E0",   # Inglaterra (Premier League)
    "SP1",  # España (La Liga)
    "I1",   # Italia (Serie A)
    "F1",   # Francia (Ligue 1)
    "D1",   # Alemania (Bundesliga)
    "N1",   # Países Bajos (Eredivisie)
    "SC0"   # Escocia (Premiership)
]

def parse_date(date_str: str) -> datetime.date:
    """Parsea la fecha en formato dd/mm/yy o dd/mm/yyyy y la retorna como datetime.date."""
    for fmt in ('%d/%m/%Y', '%d/%m/%y'):
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"No se pudo convertir la fecha: {date_str}")

def save_match_results(db: Session, data: pd.DataFrame, league: str, season: str):
    for index, row in data.iterrows():
        try:
            # Verificar si la fila es el encabezado (header)
            if row.get('Date') == 'Date':
                continue  # Saltar la fila de encabezado

            # Intentar convertir la fecha usando el nuevo método de parseo
            match_date = parse_date(row.get('Date')) if pd.notna(row.get('Date')) else None
            
            # Crear instancia de MatchResult asegurando la correcta asignación de tipos
            match = MatchResult(
                div=str(league),
                date=match_date,
                home_team=str(row.get('HomeTeam')) if pd.notna(row.get('HomeTeam')) else None,
                away_team=str(row.get('AwayTeam')) if pd.notna(row.get('AwayTeam')) else None,
                fthg=int(row.get('FTHG')) if pd.notna(row.get('FTHG')) else None,
                ftag=int(row.get('FTAG')) if pd.notna(row.get('FTAG')) else None,
                ftr=str(row.get('FTR')) if pd.notna(row.get('FTR')) else None,
                hthg=int(row.get('HTHG')) if pd.notna(row.get('HTHG')) else None,
                htag=int(row.get('HTAG')) if pd.notna(row.get('HTAG')) else None,
                htr=str(row.get('HTR')) if pd.notna(row.get('HTR')) else None,
                hs=int(row.get('HS')) if pd.notna(row.get('HS')) else None,
                as_=int(row.get('AS')) if pd.notna(row.get('AS')) else None,
                hst=int(row.get('HST')) if pd.notna(row.get('HST')) else None,
                ast=int(row.get('AST')) if pd.notna(row.get('AST')) else None,
                hc=int(row.get('HC')) if pd.notna(row.get('HC')) else None,
                ac=int(row.get('AC')) if pd.notna(row.get('AC')) else None,
                hf=int(row.get('HF')) if pd.notna(row.get('HF')) else None,
                af=int(row.get('AF')) if pd.notna(row.get('AF')) else None,
                ho=int(row.get('HO')) if pd.notna(row.get('HO')) else None,
                ao=int(row.get('AO')) if pd.notna(row.get('AO')) else None,
                hy=int(row.get('HY')) if pd.notna(row.get('HY')) else None,
                ay=int(row.get('AY')) if pd.notna(row.get('AY')) else None,
                hr=int(row.get('HR')) if pd.notna(row.get('HR')) else None,
                ar=int(row.get('AR')) if pd.notna(row.get('AR')) else None,
                hbp=int(row.get('HBP')) if pd.notna(row.get('HBP')) else None,
                abp=int(row.get('ABP')) if pd.notna(row.get('ABP')) else None,
                season=season
            )
            
            db.add(match)
        except Exception as e:
            print(f"Error al procesar la fila {index}: {row}, Error: {e}")
            continue  # Omitir la fila con errores y continuar con la siguiente

    db.commit()

@router.post("/scrape-all-seasons/")
def scrape_and_save_all_seasons(db: Session = Depends(get_db)):
    try:
        # Realizar el scraping una vez para todas las combinaciones de ligas y temporadas
        for season in seasons:
            for league in leagues:
                data = scrape_football_data([league], [season])
                if not data.empty:
                    # Guardar los datos obtenidos en la base de datos
                    save_match_results(db, data, league, season)
        
        return {"message": "Datos guardados correctamente para todas las ligas y temporadas disponibles."}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al procesar los datos: {e}")

def validate_match(match: MatchResult) -> Match:
    """Valida y ajusta los campos de un MatchResult para cumplir con el esquema de respuesta."""
    return Match(
        id=match.id,
        div=match.div or "",
        date=match.date,
        home_team=match.home_team or "",
        away_team=match.away_team or "",
        fthg=match.fthg if match.fthg is not None else 0,
        ftag=match.ftag if match.ftag is not None else 0,
        ftr=match.ftr or "",
        hthg=match.hthg if match.hthg is not None else 0,
        htag=match.htag if match.htag is not None else 0,
        htr=match.htr or "",
        hs=match.hs if match.hs is not None else 0,
        as_=match.as_ if match.as_ is not None else 0,
        hst=match.hst if match.hst is not None else 0,
        ast=match.ast if match.ast is not None else 0,
        hc=match.hc if match.hc is not None else 0,
        ac=match.ac if match.ac is not None else 0,
        hf=match.hf if match.hf is not None else 0,
        af=match.af if match.af is not None else 0,
        ho=match.ho if match.ho is not None else 0,
        ao=match.ao if match.ao is not None else 0,
        hy=match.hy if match.hy is not None else 0,
        ay=match.ay if match.ay is not None else 0,
        hr=match.hr if match.hr is not None else 0,
        ar=match.ar if match.ar is not None else 0,
        hbp=match.hbp if match.hbp is not None else 0,
        abp=match.abp if match.abp is not None else 0,
        season=match.season or ""
    )
    
@router.post("/matches/", response_model=Match)
def create_match(match: Match, db: Session = Depends(get_db)):
    db_match = MatchResult(**match.dict())
    db.add(db_match)
    db.commit()
    db.refresh(db_match)
    
    # Validar y transformar el objeto antes de devolverlo
    validated_match = validate_match(db_match)
    return validated_match

@router.get("/matches/", response_model=list[Match])
def read_matches(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    matches = db.query(MatchResult).offset(skip).limit(limit).all()
    validated_matches = [validate_match(match) for match in matches]
    return validated_matches

@router.get("/matches/{match_id}", response_model=Match)
def read_match(match_id: int, db: Session = Depends(get_db)):
    match = db.query(MatchResult).filter(MatchResult.id == match_id).first()
    if match is None:
        raise HTTPException(status_code=404, detail="Match not found")
    
    validated_match = validate_match(match)
    return validated_match

