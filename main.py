from fastapi import FastAPI
from app.api.endpoints import router as match_router
from app.db.database import init_db

init_db()

app = FastAPI()

app.include_router(match_router, prefix="/api/v1")

@app.get("/")
def read_root():
    return {"message": "Welcome to the Football Data API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
