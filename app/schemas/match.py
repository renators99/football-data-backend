from datetime import date
from pydantic import BaseModel

class Match(BaseModel):
    id: int
    div: str  # League Division
    date: date  # Match Date (dd/mm/yyyy)
    home_team: str
    away_team: str
    fthg: int  # Full Time Home Team Goals
    ftag: int  # Full Time Away Team Goals
    ftr: str  # Full Time Result (H=Home Win, D=Draw, A=Away Win)
    hthg: int  # Half Time Home Team Goals
    htag: int  # Half Time Away Team Goals
    htr: str  # Half Time Result (H=Home Win, D=Draw, A=Away Win)
    hs: int | None = None  # Home Team Shots
    as_: int | None = None  # Away Team Shots
    hst: int | None = None  # Home Team Shots on Target
    ast: int | None = None  # Away Team Shots on Target
    hc: int | None = None  # Home Team Corners
    ac: int | None = None  # Away Team Corners
    hf: int | None = None  # Home Team Fouls Committed
    af: int | None = None  # Away Team Fouls Committed
    ho: int | None = None  # Home Team Offsides
    ao: int | None = None  # Away Team Offsides
    hy: int | None = None  # Home Team Yellow Cards
    ay: int | None = None  # Away Team Yellow Cards
    hr: int | None = None  # Home Team Red Cards
    ar: int | None = None  # Away Team Red Cards
    hbp: int | None = None  # Home Team Bookings Points
    abp: int | None = None  # Away Team Bookings Points
    season: str  # Season (e.g., 2022/2023)

    class Config:
        orm_mode = True
