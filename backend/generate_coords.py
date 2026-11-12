import numpy as np
from sqlalchemy.orm import Session
from sentence_transformers import SentenceTransformer
import umap.umap_ as umap
from tqdm import tqdm
from main import SessionLocal, Sentence, engine

MODEL_NAME = 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'

def generate_and_save_coordinates():
    # --- PHASE 1: READ & CLOSE ---
    session = SessionLocal()
    print("Fetching sentences from the database...")
    records = session.query(Sentence.id, Sentence.text).filter(Sentence.x == None).all()
    session.close() # <-- CLOSE CONNECTION IMMEDIATELY
    
    if not records:
        print("No sentences found needing coordinates.")
        return
        
    ids = [r[0] for r in records]
    sentences = [r[1] for r in records]
    print(f"Loaded {len(sentences)} sentences.")

    # --- PHASE 2: AI & MATH (No active DB connection) ---
    print(f"Loading AI model: {MODEL_NAME}...")
    model = SentenceTransformer(MODEL_NAME)
    
    print("Generating sentence embeddings...")
    embeddings = model.encode(sentences, batch_size=256, show_progress_bar=True, device='cpu')
    
    print("Running UMAP to crush embeddings down to 3D...")
    reducer = umap.UMAP(
        n_components=3, 
        metric='cosine', 
        n_jobs=-1,
        random_state=42 
    )
    coords3d = reducer.fit_transform(embeddings)
    
    # --- PHASE 3: RECONNECT & SAVE ---
    print("Reconnecting to update database with X, Y, Z coordinates...")
    session = SessionLocal() # <-- REOPEN CONNECTION
    
    mappings = []
    for i in range(len(ids)):
        mappings.append({
            "id": ids[i],
            "x": float(coords3d[i][0]),
            "y": float(coords3d[i][1]),
            "z": float(coords3d[i][2])
        })
    
    chunk_size = 10000
    for i in tqdm(range(0, len(mappings), chunk_size), desc="Saving to DB"):
        session.bulk_update_mappings(Sentence, mappings[i:i + chunk_size])
        session.commit()

    print("Coordinates successfully saved!")
    session.close()

if __name__ == "__main__":
    generate_and_save_coordinates()