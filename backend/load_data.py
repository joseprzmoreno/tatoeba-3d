import os
from sqlalchemy.orm import Session
from main import SessionLocal, Sentence, engine, Base

# The TSV is one directory up from the backend folder
TSV_FILE_PATH = "../spa_sentences.tsv"
BATCH_SIZE = 10000

def load_sentences():
    # Ensure the table is created in the database
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    
    sentences_to_insert = []
    total_inserted = 0
    
    print(f"Reading from {TSV_FILE_PATH}...")
    
    try:
        with open(TSV_FILE_PATH, 'r', encoding='utf-8') as f:
            for line in f:
                # The TSV columns are separated by tabs
                parts = line.strip('\n').split('\t')
                
                # Ensure the line has at least 3 columns (ID, Lang, Text)
                if len(parts) >= 3:
                    text = parts[2]
                    
                    # Filter sentences between 16 and 160 characters
                    if 16 <= len(text) <= 160:
                        # Create the SQLAlchemy Sentence object
                        sentences_to_insert.append(Sentence(text=text))
                        
                # Bulk insert in batches to keep memory usage low and speed high
                if len(sentences_to_insert) >= BATCH_SIZE:
                    session.bulk_save_objects(sentences_to_insert)
                    session.commit()
                    total_inserted += len(sentences_to_insert)
                    print(f"Inserted {total_inserted} sentences so far...")
                    sentences_to_insert = []
                    
        # Insert any remaining sentences that didn't fill the final batch
        if sentences_to_insert:
            session.bulk_save_objects(sentences_to_insert)
            session.commit()
            total_inserted += len(sentences_to_insert)
            
        print(f"Done! Successfully loaded {total_inserted} filtered sentences into the database.")
        
    except FileNotFoundError:
        print(f"Error: Could not find the file at {TSV_FILE_PATH}. Make sure you run this script from inside the backend/ folder.")
    finally:
        session.close()

if __name__ == "__main__":
    load_sentences()