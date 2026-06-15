import { useState } from 'react';
// import './App.css';

function App() {
  const [query, setQuery] = useState('');
  const [diagnosticResult, setDiagnosticResult] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const handleDiagnose = async (e) => {
    e.preventDefault();
    
    // Reset previous states
    setIsLoading(true);
    setDiagnosticResult('');
    setError('');

    try {
      // Send the POST request to your local Flask API
      const response = await fetch('http://127.0.0.1:5000/api/diagnose', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ query: query }),
      });

      if (!response.ok) {
        throw new Error('Network response was not ok');
      }

      // Parse the JSON payload
      const data = await response.json();
      
      if (data.status === 'success') {
        setDiagnosticResult(data.diagnostic_analysis);
      } else {
        setError(data.message || 'An error occurred during diagnosis.');
      }
    } catch (err) {
      setError('Failed to connect to the backend API. Is Flask running?');
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: '800px', margin: '0 auto', padding: '2rem', fontFamily: 'system-ui, sans-serif' }}>
      <header style={{ borderBottom: '2px solid #eee', marginBottom: '2rem', paddingBottom: '1rem' }}>
        <h1 style={{ color: '#2c3e50', margin: '0 0 1.2rem 0' }}>Aviation Safety RAG System</h1>
        <p style={{ color: '#7f8c8d', margin: '0 3rem '}}>Diagnostic Query Interface powered by BGE & Llama-3</p>
      </header>

      <form onSubmit={handleDiagnose} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        <textarea
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Enter incident symptoms or diagnostic query here (e.g., 'uncommanded engine shutdown during IMC approach')..."
          rows={4}
          required
          style={{ padding: '1rem', fontSize: '1rem', borderRadius: '8px', border: '1px solid #ccc', resize: 'vertical' }}
        />
        
        <button 
          type="submit" 
          disabled={isLoading || !query.trim()}
          style={{ 
            padding: '1rem', 
            fontSize: '1rem', 
            backgroundColor: isLoading ? '#95a5a6' : '#2980b9', 
            color: 'white', 
            border: 'none', 
            borderRadius: '8px', 
            cursor: isLoading ? 'not-allowed' : 'pointer',
            fontWeight: 'bold'
          }}
        >
          {isLoading ? 'Analyzing ASRS Database...' : 'Run Diagnostics'}
        </button>
      </form>

      {error && (
        <div style={{ marginTop: '2rem', padding: '1rem', backgroundColor: '#fee', color: '#c0392b', borderRadius: '8px' }}>
          <strong>Error:</strong> {error}
        </div>
      )}

      {diagnosticResult && (
        <div style={{ marginTop: '2rem', padding: '1.5rem', backgroundColor: '#f8f9fa', border: '1px solid #e9ecef', borderRadius: '8px' }}>
          <h2 style={{ color: '#2c3e50', marginTop: 0, fontSize: '1.2rem' }}>Diagnostic Analysis</h2>
          <p style={{ whiteSpace: 'pre-wrap', lineHeight: '1.6', color: '#34495e', margin: 0 }}>
            {diagnosticResult}
          </p>
        </div>
      )}
    </div>
  );
}

export default App;