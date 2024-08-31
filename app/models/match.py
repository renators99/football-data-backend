from sqlalchemy import Column, Integer, String, Date
from app.utils.database import Base

class MatchResult(Base):
    __tablename__ = "match_results"
    
    id = Column(Integer, primary_key=True, index=True)
    div = Column(String, index=True)
    date = Column(Date)  # Campo de fecha
    home_team = Column(String)
    away_team = Column(String)
    fthg = Column(Integer)  # Goles del equipo local
    ftag = Column(Integer)  # Goles del equipo visitante
    ftr = Column(String)  # Resultado final
    hthg = Column(Integer, nullable=True)  # Goles al medio tiempo del equipo local
    htag = Column(Integer, nullable=True)  # Goles al medio tiempo del equipo visitante
    htr = Column(String, nullable=True)  # Resultado al medio tiempo
    hs = Column(Integer, nullable=True)  # Tiros del equipo local
    as_ = Column(Integer, nullable=True)  # Tiros del equipo visitante
    hst = Column(Integer, nullable=True)  # Tiros a puerta del equipo local
    ast = Column(Integer, nullable=True)  # Tiros a puerta del equipo visitante
    hc = Column(Integer, nullable=True)  # Córners del equipo local
    ac = Column(Integer, nullable=True)  # Córners del equipo visitante
    hf = Column(Integer, nullable=True)  # Faltas cometidas por el equipo local
    af = Column(Integer, nullable=True)  # Faltas cometidas por el equipo visitante
    ho = Column(Integer, nullable=True)  # Fuera de juego del equipo local
    ao = Column(Integer, nullable=True)  # Fuera de juego del equipo visitante
    hy = Column(Integer, nullable=True)  # Tarjetas amarillas del equipo local
    ay = Column(Integer, nullable=True)  # Tarjetas amarillas del equipo visitante
    hr = Column(Integer, nullable=True)  # Tarjetas rojas del equipo local
    ar = Column(Integer, nullable=True)  # Tarjetas rojas del equipo visitante
    hbp = Column(Integer, nullable=True)  # Puntos de penalización del equipo local
    abp = Column(Integer, nullable=True)  # Puntos de penalización del equipo visitante
    season = Column(String)  # Temporada, ahora al final
