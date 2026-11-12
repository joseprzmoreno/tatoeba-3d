import os
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, Float, func
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from pydantic import BaseModel
from typing import List
from googletrans import Translator
from fastapi import HTTPException

# --- Database Setup ---
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://tatoeba_user:supersecretpassword@localhost:15432/tatoeba_db")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Sentence(Base):
    __tablename__ = "sentences"
    id = Column(Integer, primary_key=True, index=True)
    text = Column(String, index=True)
    translated_text = Column(String, nullable=True)
    x = Column(Float, index=True)
    y = Column(Float, index=True)
    z = Column(Float, index=True)

Base.metadata.create_all(bind=engine)

# --- Pydantic Models (Schemas for API output) ---
class SentenceBase(BaseModel):
    id: int
    text: str
    x: float
    y: float
    z: float

    class Config:
        from_attributes = True

class SentenceDetail(SentenceBase):
    target_lang: str
    translated_text: str

# --- FastAPI App Setup ---
app = FastAPI()

# Enable CORS so the React frontend on port 15173 can fetch data
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict this to your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency to get the DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Endpoints ---

@app.get("/")
def read_root():
    return {"status": "Backend running, Database populated", "port": 18000}

@app.get("/api/sentences/nearby", response_model=List[SentenceBase])
def get_nearby_sentences(
    x: float, 
    y: float, 
    z: float, 
    radius: float = Query(5.0, description="Radius of the reasonable circle"), 
    db: Session = Depends(get_db)
):
    """
    Returns up to 10 sentences within a 3D sphere (radius) of the given coordinates.
    """
    # Calculate 3D Euclidean distance: sqrt((x2-x1)^2 + (y2-y1)^2 + (z2-z1)^2)
    distance_expr = func.sqrt(
        func.pow(Sentence.x - x, 2) + 
        func.pow(Sentence.y - y, 2) + 
        func.pow(Sentence.z - z, 2)
    )

    nearby_sentences = (
        db.query(Sentence)
        .filter(Sentence.x.isnot(None)) # Ensure coordinates exist
        .filter(distance_expr <= radius)
        .order_by(distance_expr) # Closest first
        .limit(10)
        .all()
    )
    
    return nearby_sentences

@app.get("/api/sentences/random", response_model=SentenceBase)
def get_random_sentence(db: Session = Depends(get_db)):
    """
    Picks a completely random sentence from the database to ensure 
    we always land in a populated area of the 3D space.
    """
    random_sentence = (
        db.query(Sentence)
        .filter(Sentence.x.isnot(None))
        .order_by(func.random())
        .first()
    )
    
    if not random_sentence:
        raise HTTPException(status_code=404, detail="No sentences found")
        
    return random_sentence

translator = Translator()

def translate_es_to_target(text: str, target_lang: str) -> str:
    """Translates text using the py-googletrans library."""
    try:
        # googletrans uses 'dest' instead of 'target'
        result = translator.translate(text, src='es', dest=target_lang)
        return result.text
    except Exception as e:
        print(f"Googletrans error: {e}")
        return f"[Translation Error] {text}"

@app.get("/api/sentences/{sentence_id}", response_model=SentenceDetail)
def get_sentence_detail(
    sentence_id: int, 
    lang: str = Query(..., description="Target language code (e.g., 'en', 'fr', 'de')"), 
    db: Session = Depends(get_db)
):
    """
    Returns the specific sentence and its live Google translation.
    """
    sentence = db.query(Sentence).filter(Sentence.id == sentence_id).first()
    
    if not sentence:
        raise HTTPException(status_code=404, detail="Sentence not found")
        
    # Call the live translation function
    real_translation = translate_es_to_target(sentence.text, lang)
    
    return {
        "id": sentence.id,
        "text": sentence.text,
        "x": sentence.x,
        "y": sentence.y,
        "z": sentence.z,
        "target_lang": lang,
        "translated_text": real_translation
    }

