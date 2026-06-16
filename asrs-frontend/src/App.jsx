import { useState, useRef, useEffect } from 'react';

function App() {
  const [sessions, setSessions] = useState([]);
  const [activeSessionId, setActiveSessionId] = useState(null);
  const [currentInput, setCurrentInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isPageLoading, setIsPageLoading] = useState(true);
  
  const messagesEndRef = useRef(null);

  useEffect(() => {
    const fetchSessions = async () => {
      try {
        const res = await fetch('http://127.0.0.1:5000/api/sessions');
        const data = await res.json();
        setSessions(data);
        if (data.length > 0) {
          setActiveSessionId(data[0].id);
        } else {
          setActiveSessionId(null);
        }
      } catch (err) {
        console.error("Failed to load sessions:", err);
      } finally {
        setIsPageLoading(false);
      }
    };
    fetchSessions();
  }, []);

  const activeSession = sessions.find(s => s.id === activeSessionId) || { title: '', messages: [] };
  const activeMessages = activeSession.messages;

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [activeMessages]);

  const createNewSession = async () => {
    try {
      const res = await fetch('http://127.0.0.1:5000/api/sessions', { method: 'POST' });
      const newSession = await res.json();
      setSessions([newSession, ...sessions]);
      setActiveSessionId(newSession.id);
    } catch (err) {
      console.error("Failed to create session:", err);
    }
  };

  const deleteSession = async (e, idToDelete) => {
    e.stopPropagation();
    try {
      await fetch(`http://127.0.0.1:5000/api/sessions/${idToDelete}`, { method: 'DELETE' });
      const updatedSessions = sessions.filter(s => s.id !== idToDelete);
      setSessions(updatedSessions);
      
      if (activeSessionId === idToDelete) {
        setActiveSessionId(updatedSessions.length > 0 ? updatedSessions[0].id : null);
      }
      
      // Removed the React auto-creation logic here so it stays empty!
    } catch (err) {
      console.error("Failed to delete session:", err);
    }
  };

  const handleDiagnose = async (e) => {
    e.preventDefault();
    if (!currentInput.trim() || !activeSessionId) return;

    const userText = currentInput;
    setCurrentInput('');
    setIsLoading(true);

    setSessions(prevSessions => prevSessions.map(session => {
      if (session.id === activeSessionId) {
        return {
          ...session,
          title: session.messages.length === 0 ? userText.substring(0, 25) + '...' : session.title,
          messages: [
            ...session.messages, 
            { sender: 'user', text: userText },
            { sender: 'ai', text: '' } 
          ]
        };
      }
      return session;
    }));

    try {
      const response = await fetch('http://127.0.0.1:5000/api/diagnose', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: userText, session_id: activeSessionId }),
      });

      if (!response.ok) throw new Error('Network response was not ok');

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let accumulatedText = "";

      setIsLoading(false);

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        const chunkText = decoder.decode(value, { stream: true });
        accumulatedText += chunkText;

        setSessions(prevSessions => prevSessions.map(session => {
          if (session.id === activeSessionId) {
            const updatedMessages = [...session.messages];
            if (updatedMessages.length > 0) {
              updatedMessages[updatedMessages.length - 1] = { 
                sender: 'ai', 
                text: accumulatedText.trimStart() 
              };
            }
            return { ...session, messages: updatedMessages };
          }
          return session;
        }));
      }

    } catch (err) {
      console.error(err);
      setIsLoading(false);
      setSessions(prevSessions => prevSessions.map(session => {
        if (session.id === activeSessionId) {
          return {
            ...session,
            messages: [...session.messages, { sender: 'system', text: 'Failed to connect to backend API.' }]
          };
        }
        return session;
      }));
    }
  };

  if (isPageLoading) return <div style={{ padding: '2rem', textAlign: 'center' }}>Connecting to Database...</div>;

  return (
    <div style={{ height: '100vh', width: '100vw', display: 'flex', flexDirection: 'row', fontFamily: 'system-ui, sans-serif', backgroundColor: '#e1f5fe' }}>
      
      {/* SIDEBAR */}
      <aside style={{ width: '280px', backgroundColor: '#01579b', display: 'flex', flexDirection: 'column', color: 'white', borderRight: '1px solid #0277bd', zIndex: 20 }}>
        <div style={{ padding: '1.5rem', borderBottom: '1px solid rgba(255,255,255,0.1)' }}>
          <h2 style={{ margin: '0 0 1rem 0', fontSize: '1.2rem', color: '#b3e5fc' }}>ASRS Workspace</h2>
          <button 
            onClick={createNewSession}
            style={{ width: '100%', padding: '0.8rem', backgroundColor: '#0288d1', color: 'white', border: 'none', borderRadius: '8px', cursor: 'pointer', fontWeight: 'bold', display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '0.5rem' }}
          >
            <span>+</span> New Diagnostic
          </button>
        </div>

        <div style={{ flexGrow: 1, overflowY: 'auto', padding: '1rem' }}>
          <p style={{ fontSize: '0.8rem', color: '#81d4fa', textTransform: 'uppercase', letterSpacing: '1px', marginBottom: '1rem' }}>Saved Sessions</p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            {sessions.map(session => (
              <div 
                key={session.id}
                onClick={() => setActiveSessionId(session.id)}
                style={{
                  display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0.8rem',
                  backgroundColor: session.id === activeSessionId ? '#0277bd' : 'transparent',
                  borderRadius: '8px', cursor: 'pointer', fontSize: '0.9rem', border: session.id === activeSessionId ? '1px solid #4fc3f7' : '1px solid transparent'
                }}
              >
                <div style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', paddingRight: '10px' }}>
                  {session.title}
                </div>
                
                <button 
                  onClick={(e) => deleteSession(e, session.id)}
                  style={{ background: 'none', border: 'none', color: '#81d4fa', cursor: 'pointer', fontSize: '1.2rem', padding: '0 5px', fontWeight: 'bold' }}
                  title="Delete Session"
                >
                  ×
                </button>
              </div>
            ))}
          </div>
        </div>
      </aside>

      {/* MAIN CHAT AREA - CONDITIONAL RENDERING */}
      {sessions.length === 0 ? (
        // THE EMPTY STATE UI
        <main style={{ flexGrow: 1, display: 'flex', justifyContent: 'center', alignItems: 'center', backgroundColor: '#ffffff', height: '100vh' }}>
          <div style={{ textAlign: 'center' }}>
            <h2 style={{ color: '#0277bd', marginBottom: '2rem' }}>No Active Diagnostic Sessions</h2>
            <button 
              onClick={createNewSession}
              style={{ padding: '1rem 2.5rem', fontSize: '1.2rem', backgroundColor: '#0288d1', color: 'white', border: 'none', borderRadius: '8px', cursor: 'pointer', fontWeight: 'bold', boxShadow: '0 4px 15px rgba(0,0,0,0.1)' }}
            >
              + Create New Session
            </button>
          </div>
        </main>
      ) : (
        // THE NORMAL CHAT UI
        <main style={{ flexGrow: 1, display: 'flex', flexDirection: 'column', height: '100vh', position: 'relative' }}>
          <header style={{ backgroundColor: '#ffffff', padding: '1.5rem 2rem', boxShadow: '0 2px 10px rgba(0,0,0,0.05)', zIndex: 10 }}>
            <h1 style={{ color: '#0277bd', margin: '0 0 0.2rem 0', fontSize: '1.5rem' }}>{activeSession?.title || 'No Session Active'}</h1>
            <p style={{ color: '#546e7a', margin: 0, fontSize: '0.9rem' }}>Powered by BGE & Llama-3</p>
          </header>

          <div style={{ flexGrow: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '1.5rem', padding: '2rem 2rem 6rem 2rem' }}>
            {activeMessages.length === 0 && (
              <div style={{ textAlign: 'center', color: '#78909c', margin: 'auto' }}>
                <h3 style={{ color: '#0277bd' }}>Ready for Analysis</h3>
                <p>Type an incident symptom below to query the database.</p>
              </div>
            )}

            {activeMessages.map((msg, index) => (
              <div key={index} style={{ alignSelf: msg.sender === 'user' ? 'flex-start' : 'flex-end', maxWidth: '75%', display: 'flex', flexDirection: 'column' }}>
                <span style={{ fontSize: '0.85rem', color: '#78909c', marginBottom: '0.3rem', alignSelf: msg.sender === 'user' ? 'flex-start' : 'flex-end' }}>
                  {msg.sender === 'user' ? 'Safety Inspector' : msg.sender === 'ai' ? 'Diagnostic AI' : 'System Alert'}
                </span>
                <div style={{
                  backgroundColor: msg.sender === 'user' ? '#ffffff' : msg.sender === 'system' ? '#ffebee' : '#0288d1',
                  color: msg.sender === 'user' ? '#263238' : msg.sender === 'system' ? '#c62828' : '#ffffff',
                  padding: '1.2rem', borderRadius: msg.sender === 'user' ? '0 16px 16px 16px' : '16px 0 16px 16px',
                  boxShadow: '0 4px 6px rgba(0,0,0,0.05)', border: msg.sender === 'user' ? '1px solid #b3e5fc' : 'none',
                  lineHeight: '1.6', whiteSpace: 'pre-wrap'
                }}>
                  {msg.text}
                </div>
              </div>
            ))}

            {isLoading && (
              <div style={{ alignSelf: 'flex-end', maxWidth: '75%', display: 'flex', flexDirection: 'column' }}>
                 <span style={{ fontSize: '0.85rem', color: '#78909c', marginBottom: '0.3rem', alignSelf: 'flex-end' }}>Diagnostic AI</span>
                 <div style={{ backgroundColor: '#e1e2e1', color: '#424242', padding: '1.2rem', borderRadius: '16px 0 16px 16px', fontStyle: 'italic' }}>
                   Analyzing ASRS vector database...
                 </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          <div style={{ position: 'absolute', bottom: 0, left: 0, right: 0, padding: '1.5rem', background: 'linear-gradient(transparent, #e1f5fe 20%)' }}>
            <form onSubmit={handleDiagnose} style={{ maxWidth: '1000px', margin: '0 auto', display: 'flex', gap: '1rem', backgroundColor: '#ffffff', padding: '1rem', borderRadius: '12px', boxShadow: '0 4px 15px rgba(0,0,0,0.08)', border: '1px solid #b3e5fc' }}>
              <input
                value={currentInput}
                onChange={(e) => setCurrentInput(e.target.value)}
                placeholder="Type incident symptoms..."
                disabled={isLoading || !activeSessionId}
                style={{ flexGrow: 1, padding: '0.5rem', fontSize: '1rem', border: 'none', outline: 'none', backgroundColor: 'transparent' }}
              />
              <button 
                type="submit" 
                disabled={isLoading || !currentInput.trim() || !activeSessionId}
                style={{ padding: '0.8rem 2rem', fontSize: '1rem', backgroundColor: isLoading || !currentInput.trim() ? '#b0bec5' : '#0277bd', color: 'white', border: 'none', borderRadius: '8px', cursor: isLoading || !currentInput.trim() ? 'not-allowed' : 'pointer', fontWeight: 'bold' }}
              >
                Send
              </button>
            </form>
          </div>
        </main>
      )}
    </div>
  );
}

export default App;