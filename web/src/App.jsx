import { useState, useRef, useEffect } from 'react'
import './App.css'

const API_BASE = import.meta.env.VITE_API_URL || ''

function App() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const chatRef = useRef(null)

  useEffect(() => {
    if (chatRef.current) {
      chatRef.current.scrollTop = chatRef.current.scrollHeight
    }
  }, [messages])

  async function send() {
    const text = input.trim()
    if (!text || loading) return

    setMessages(prev => [...prev, { role: 'user', content: text }])
    setInput('')
    setLoading(true)

    try {
      const response = await fetch('/query', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query: text,
          mode: 'hybrid',
        }),
      })

      if (!response.ok) {
        const errorText = await response.text()
        throw new Error(`HTTP ${response.status}: ${errorText}`)
      }

      const data = await response.json()
      
      setMessages(prev => [...prev, { 
        role: 'agent', 
        content: data.response || 'No response',
        intent: data.intent || 'casual'
      }])
    } catch (err) {
      setMessages(prev => [...prev, { 
        role: 'agent', 
        content: `Error: ${err.message}`,
        intent: 'error'
      }])
    } finally {
      setLoading(false)
    }
  }

  function onKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      send()
    }
  }

  return (
    <div className="app">
      <header className="header">
        <div className={`dot ${!loading ? 'online' : 'offline'}`} />
        <h1>Porthon Agent</h1>
        <span className="status">{loading ? 'thinking...' : 'ready'}</span>
      </header>

      <div className="chat" ref={chatRef}>
        {messages.length === 0 && (
          <div className="welcome">
            <h2>Hey, Theo.</h2>
            <p>Ask me anything — about your finances, patterns, goals, or just talk.</p>
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={`message ${msg.role}`}>
            {msg.role === 'agent' && msg.intent && msg.intent !== 'casual' && msg.intent !== 'error' && (
              <span className="badge">{msg.intent}</span>
            )}
            <div className="content">{msg.content}</div>
          </div>
        ))}

        {loading && (
          <div className="typing">thinking...</div>
        )}
      </div>

      <div className="input-area">
        <textarea
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder="Type a message..."
          rows={1}
          disabled={loading}
        />
        <button onClick={send} disabled={loading || !input.trim()}>
          Send
        </button>
      </div>
    </div>
  )
}

export default App
