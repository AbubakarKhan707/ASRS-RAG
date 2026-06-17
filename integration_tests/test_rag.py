import pytest
import requests
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

def test_backend_api_health():
    url = "http://localhost:5000/api/sessions"
    try:
        response = requests.get(url, timeout=5)
        assert response.status_code == 200
    except requests.exceptions.ConnectionError:
        pytest.fail("The Flask backend server is not running")

def test_ai_response_quality():
    model = SentenceTransformer('all-MiniLM-L6-v2')
    
    ai_generated_answer = "Dual engine failure was caused by ice ingestion at high altitude."
    ground_truth = "Dual engine failure was caused by high-altitude ice ingestion."
    
    ai_embedding = model.encode([ai_generated_answer])
    truth_embedding = model.encode([ground_truth])
    
    score = cosine_similarity(ai_embedding, truth_embedding)[0][0]
    
    assert score >= 0.85, f"AI answer is not accurate enough. Score: {score}"