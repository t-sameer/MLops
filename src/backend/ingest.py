import json
import sqlite3
import chromadb
from sentence_transformers import SentenceTransformer
import os

# Ensure we are using the mounted data volume
DATA_DIR = "/app/data"
JSON_PATH = os.path.join(DATA_DIR, "telecom_sops_500_stress_test.json")
SQLITE_PATH = os.path.join(DATA_DIR, "telecom_sops.db")
CHROMA_PATH = os.path.join(DATA_DIR, "chroma_db")

def ingest_data():
    print("Loading JSON data...")
    with open(JSON_PATH, 'r') as f:
        sops = json.load(f)

    print("Initializing SQLite...")
    conn = sqlite3.connect(SQLITE_PATH)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS sops (id TEXT, content TEXT)''')

    print("Initializing ChromaDB & BGE Model...")
    chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
    collection = chroma_client.get_or_create_collection(name="sops")
    embedder = SentenceTransformer('BAAI/bge-base-en-v1.5')

    print(f"Embedding {len(sops)} SOPs. This will take a moment on the CPU...")
    for sop in sops:
        sop_id = sop['sop_id']
        content = sop['search_content']
        
        # 1. Save to SQLite
        cursor.execute("INSERT OR REPLACE INTO sops VALUES (?, ?)", (sop_id, json.dumps(sop)))
        
        # 2. Save to Chroma
        embedding = embedder.encode(content).tolist()
        collection.add(
            ids=[sop_id],
            embeddings=[embedding],
            documents=[content],
            metadatas=[{"vendor": sop.get("vendor", "Unknown")}]
        )

    conn.commit()
    conn.close()
    print("Ingestion Complete! Databases generated in /app/data/")

if __name__ == "__main__":
    ingest_data()