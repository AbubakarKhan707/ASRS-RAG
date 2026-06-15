from flask import Flask, request, jsonify
from flask_cors import CORS
import ollama
import time
from query_engine import LocalAviationRAG

app = Flask(__name__)
# Enable CORS for all routes so frontend applications can connect
CORS(app)

# Initialize your heavy RAG infrastructure once when the web server boots up
print("[System]: Loading RAG vector database and embedding models into memory...")
rag_system = LocalAviationRAG(model_name="llama3")

def fetch_complete_response(system_instruction, user_query):
    # Accumulates streaming tokens from Ollama into a single string for the HTTP response
    response = ollama.chat(
        model=rag_system.llm_model,
        messages=[
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": user_query}
        ],
        stream=False
    )

    return response['message']['content']

@app.route('/api/diagnose', methods=['POST'])
def diagnose_incident():
    try:
        # 1. Parse incoming JSON request payload
        data = request.get_json()
        if not data or 'query' not in data:
            return jsonify({
                "status": "error",
                "message": "Missing required field: 'query'"
            }), 400
            
        user_query = data['query']
        
        # 2. Execute vector search to gather background context from Qdrant
        print(f"\n[API Request Received]: {user_query}")
        context = rag_system.retrieve_context(user_query, top_k=2)
        
        # 3. Construct the protective grounding system prompt
        system_instruction = (
            "You are an expert aviation safety investigator and maintenance AI assistant. "
            "Your task is to answer the user's technical query using ONLY the provided incident reference documents. "
            "If the documents do not contain enough specific operational facts to answer the question, "
            "state clearly that you lack sufficient data. Do not make up facts or extrapolate beyond the text.\n\n"
            f"=== CONTEXT DOCUMENTS ===\n{context}\n"
        )
        
        # 4. Generate the final answer from the local LLM
        print("[API Processing]: Querying local model via Ollama...")
        diagnostic_answer = fetch_complete_response(system_instruction, user_query)
        
        # 5. Return a structured JSON network response
        return jsonify({
            "status": "success",
            "query": user_query,
            "diagnostic_analysis": diagnostic_answer
        }), 200

    except Exception as e:
        print(f"[API Error]: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "Internal server processing failure"
        }), 500

if __name__ == '__main__':
    # Run the local web server on port 5000
    print("[System]: Launching Flask API Server on http://127.0.0.1:5000")
    app.run(host='127.0.0.1', port=5000, debug=False)