import os
import json
import sqlite3
import chromadb
import hvac
import time
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer, CrossEncoder
from gliner import GLiNER
from groq import Groq

app = FastAPI()

# --- NEW: JSON Logging Middleware for ELK Stack ---
@app.middleware("http")
async def json_logging_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    
    # Create the exact JSON format your rubric requested
    log_data = {
        "latency": round(process_time, 4),
        "query": str(request.url.path),
        "method": request.method,
        "status": response.status_code
    }
    
    # Print as a JSON string so K8s captures it, and Filebeat parses it
    print(json.dumps(log_data))
    
    return response

# Configuration
DATA_DIR = "/app/data"
SQLITE_PATH = os.path.join(DATA_DIR, "telecom_sops.db")
CHROMA_PATH = os.path.join(DATA_DIR, "chroma_db")

# --- NEW: Secure Vault Integration ---
print("Connecting to HashiCorp Vault...")
try:
    vault_client = hvac.Client(
        url=os.getenv("VAULT_ADDR", "http://vault:8200"),
        token=os.getenv("VAULT_TOKEN")
    )
    # Read the secret injected into Vault
    secret_response = vault_client.secrets.kv.v2.read_secret_version(path='llm-credentials')
    GROQ_API_KEY = secret_response['data']['data']['groq_key']
    print("SUCCESS: API Key retrieved securely from Vault.")
except Exception as e:
    print(f"CRITICAL: Failed to retrieve API key from Vault. Did you inject it? Error: {e}")
    GROQ_API_KEY = "missing_key"

# 1. CPU-Only Model Initialization
# Explicitly setting device='cpu' ensures it doesn't search for missing NVIDIA drivers
print("Loading Models into RAM (CPU Mode)...")
bi_encoder = SentenceTransformer('BAAI/bge-base-en-v1.5', device='cpu')
cross_encoder = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2', device='cpu')
ner_model = GLiNER.from_pretrained("urchade/gliner_medium-v2.1")
client = Groq(api_key=GROQ_API_KEY)

class QueryRequest(BaseModel):
    question: str

def get_db_connection():
    return sqlite3.connect(SQLITE_PATH)

@app.post("/ask")
async def ask_question(request: QueryRequest):
    try:
        # Step A: Entity Extraction (GLiNER)
        entities = ner_model.predict_entities(request.question, labels=["vendor", "device", "protocol"])
        
        # Step B: Vector Search (ChromaDB)
        chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
        collection = chroma_client.get_collection(name="sops")
        query_embedding = bi_encoder.encode(request.question).tolist()
        
        results = collection.query(query_embeddings=[query_embedding], n_results=5)
        
        if not results['ids'][0]:
            return {"answer": "No relevant SOPs found in the database.", "sources": []}
            
        doc_ids = results['ids'][0]

        # Step C: Reranking (Cross-Encoder)
        conn = get_db_connection()
        cursor = conn.cursor()
        candidates = []
        for doc_id in doc_ids:
            cursor.execute("SELECT content FROM sops WHERE id = ?", (doc_id,))
            row = cursor.fetchone()
            if row:
                candidates.append(json.loads(row[0]))
        conn.close()

        # In a full setup, you would score these with the cross_encoder here.
        # For this MVP test, we take the top 3 from the bi-encoder to save CPU cycles.
        top_candidates = candidates[:3]

        # Step D: Final Generation (Groq LLM)
        context = "\n---\n".join([c['search_content'] for c in top_candidates])
        prompt = f"Use the following telecom SOP context to answer the NOC engineer's question: {request.question}\n\nContext:\n{context}"
        
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}]
        )
        
        return {"answer": completion.choices[0].message.content, "sources": doc_ids[:3]}

    except Exception as e:
        print(f"Error processing query: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def health():
    return {"status": "Backend is running"}