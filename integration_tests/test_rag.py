import os
import pytest
import requests
from ragas import evaluate
from ragas.metrics import faithfulness, context_precision
from datasets import Dataset

# 1. Endpoint Test
def test_backend_api_health():
    # Checks if the sessions endpoint responds successfully
    url = "http://localhost:5000/api/sessions"
    try:
        response = requests.get(url, timeout=5)
        assert response.status_code == 200
    except requests.exceptions.ConnectionError:
        pytest.fail("The Flask backend server is not running or accessible.")

# 2. AI Evaluation Test
def test_ai_response_quality():
    # A sample diagnostic query to test the RAG engine
    user_query = "What causes dual engine failure according to flight records?"
    
    # Simulating the retrieved data and AI generation for evaluation
    # In a live test, you can hook this directly to your query engine output
    test_data = {
        "question": [user_query],
        "contexts": [["The aircraft suffered a dual engine loss due to high-altitude ice ingestion as recorded in incident reports."]],
        "answer": ["Dual engine failure was caused by ice ingestion at high altitude."],
        "ground_truth": ["Dual engine failure was caused by high-altitude ice ingestion."]
    }
    
    # Convert into the dataset format required by RAGAS
    dataset = Dataset.from_dict(test_data)
    
    # Evaluate the metrics
    score = evaluate(
        dataset,
        metrics=[faithfulness, context_precision]
    )
    
    # Extract scores
    faithfulness_score = score["faithfulness"]
    precision_score = score["context_precision"]
    
    # Ensure the AI meets your minimum quality threshold (e.g., 80%)
    assert faithfulness_score >= 0.80, f"AI faithfulness is too low: {faithfulness_score}"
    assert precision_score >= 0.80, f"Context precision is too low: {precision_score}"