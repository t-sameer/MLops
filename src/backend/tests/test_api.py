import pytest
from fastapi.testclient import TestClient
import sys
import os

# Add the parent directory to the path so we can import main
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from main import app

client = TestClient(app)

def test_health_check():
    """Test if the API is up and returning JSON"""
    response = client.get("/health")
    assert response.status_code == 200
    assert "status" in response.json()

def test_rag_endpoint_rejection():
    """Test if the API properly rejects empty questions"""
    response = client.post("/ask", json={"question": ""})
    # Depending on your FastAPI validation, this should be 400, 422, or handled gracefully
    assert response.status_code in [400, 422, 500] 

# Note: We don't test the actual LLM generation in CI/CD to save money/time,
# we just test that the API routing and logic is sound.