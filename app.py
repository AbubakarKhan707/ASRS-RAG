import sqlite3
import uuid
import atexit
from flask import Flask, request, jsonify, g, Response, stream_with_context
from flask_cors import CORS
from query_engine import LocalAviationRAG

app = Flask(__name__)
CORS(app)

DATABASE = 'chat_history.db'

print("[System]: Loading RAG vector database and embedding models into memory...")
rag_system = LocalAviationRAG(model_name="phi3")

def cleanup_qdrant():
    print("\n[System]: Closing Qdrant connection safely...")
    if hasattr(rag_system, 'qdrant') and hasattr(rag_system.qdrant, 'close'):
        rag_system.qdrant.close()

atexit.register(cleanup_qdrant)

# --- DATABASE SETUP ---
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                sender TEXT NOT NULL,
                text TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE
            )
        ''')
        db.commit()

init_db()

# --- API ENDPOINTS ---

@app.route('/api/sessions', methods=['GET'])
def get_sessions():
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT * FROM sessions ORDER BY rowid DESC')
    sessions = cursor.fetchall()
    
    result = []
    for session in sessions:
        session_id = session['id']
        cursor.execute('SELECT sender, text FROM messages WHERE session_id = ? ORDER BY id ASC', (session_id,))
        messages = cursor.fetchall()
        result.append({
            "id": session_id,
            "title": session['title'],
            "messages": [{"sender": m['sender'], "text": m['text']} for m in messages]
        })
        
    return jsonify(result), 200

@app.route('/api/sessions', methods=['POST'])
def create_session():
    db = get_db()
    cursor = db.cursor()
    new_id = str(uuid.uuid4())
    title = 'New Diagnostic Session'
    
    cursor.execute('INSERT INTO sessions (id, title) VALUES (?, ?)', (new_id, title))
    db.commit()
    return jsonify({"id": new_id, "title": title, "messages": []}), 201

@app.route('/api/sessions/<session_id>', methods=['DELETE'])
def delete_session(session_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute('DELETE FROM sessions WHERE id = ?', (session_id,))
    cursor.execute('DELETE FROM messages WHERE session_id = ?', (session_id,))
    db.commit()
    return jsonify({"status": "success"}), 200

@app.route('/api/diagnose', methods=['POST'])
def diagnose_incident():
    try:
        data = request.get_json()
        user_query = data.get('query')
        session_id = data.get('session_id')
        
        if not user_query or not session_id:
            return jsonify({"status": "error", "message": "Missing query or session_id"}), 400

        db = get_db()
        cursor = db.cursor()
        cursor.execute('INSERT INTO messages (session_id, sender, text) VALUES (?, ?, ?)', (session_id, 'user', user_query))
        
        cursor.execute('SELECT COUNT(*) FROM messages WHERE session_id = ?', (session_id,))
        if cursor.fetchone()[0] == 1:
            new_title = (user_query[:25] + '...') if len(user_query) > 25 else user_query
            cursor.execute('UPDATE sessions SET title = ? WHERE id = ?', (new_title, session_id))
            
        db.commit()

        # Retrieve RAG context documents
        print("\n[System]: Retrieving documents from Qdrant...", flush=True)
        context = rag_system.retrieve_context(user_query, top_k=2)
        print(f"[System]: Found {len(context.split('--- Reference Document')) - 1} documents.", flush=True)
        
        system_instruction = (
            "You are an expert aviation safety investigator and maintenance AI assistant. "
            "Your task is to answer the user's technical query using ONLY the provided incident reference documents. "
            "If the documents do not contain enough specific operational facts to answer the question, "
            "state clearly that you lack sufficient data. Do not make up facts or extrapolate beyond the text.\n\n"
            f"=== CONTEXT DOCUMENTS ===\n{context}\n"
        )

        def generate_chunks():
            yield " "
            print(f"[System]: Requesting stream from {rag_system.llm_model}...", flush=True)
            
            try:
                response_stream = rag_system.ollama_client.chat(
                    model=rag_system.llm_model,
                    messages=[
                        {"role": "system", "content": system_instruction},
                        {"role": "user", "content": user_query}
                    ],
                    stream=True
                )
                
                full_ai_response = ""
                for chunk in response_stream:
                    text_chunk = chunk['message']['content']
                    print(text_chunk, end='', flush=True)  # Print the AI's thoughts live to terminal
                    full_ai_response += text_chunk
                    yield text_chunk

                print("\n[System]: Stream finished successfully.", flush=True)

                with sqlite3.connect(DATABASE) as backup_db:
                    backup_cursor = backup_db.cursor()
                    backup_cursor.execute(
                        'INSERT INTO messages (session_id, sender, text) VALUES (?, ?, ?)', 
                        (session_id, 'ai', full_ai_response)
                    )
                    backup_db.commit()

            except Exception as stream_error:
                error_msg = f"\n[Stream Error]: Connection to AI failed: {str(stream_error)}"
                print(error_msg, flush=True)
                yield " (An error occurred while generating the response. Please check the backend logs.)"

        return Response(
            stream_with_context(generate_chunks()), 
            content_type='text/plain; charset=utf-8'
        )

    except Exception as e:
        print(f"[API Error]: {str(e)}", flush=True)
        return jsonify({"status": "error", "message": "Internal server processing failure"}), 500
    
    # Second CI pipeline test

if __name__ == '__main__':
    print("[System]: Launching Flask API Server inside Docker on port 5000", flush=True)
    app.run(host='0.0.0.0', port=5000, debug=False)