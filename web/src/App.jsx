import { useState, useRef, useEffect } from 'react'
import './App.css'

// In dev mode, Vite proxies /ws and /chat to localhost:8888
// In production, set VITE_API_URL to the backend host
const API_BASE = import.meta.env.VITE_API_URL || ''

function App() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [connected, setConnected] = useState(false)
  const [streaming, setStreaming] = useState(false)
  const wsRef = useRef(null)
  const chatRef = useRef(null)
  const sessionId = useRef('s-' + Math.random().toString(36).slice(2, 9))

  useEffect(() => {
    connect()
    return () => wsRef.current?.close()
  }, [])

  useEffect(() => {
    if (chatRef.current) {
      chatRef.current.scrollTop = chatRef.current.scrollHeight
    }
  }, [messages])

  function connect() {
    const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = API_BASE ? API_BASE.replace(/^https?:\/\//, '') : window.location.host
    const ws = new WebSocket(`${proto}//${host}/ws/${sessionId.current}`)

    ws.onopen = () => setConnected(true)
    ws.onclose = () => {
      setConnected(false)
      setTimeout(connect, 3000)
    }

    ws.onmessage = (e) => {
      const data = JSON.parse(e.data)

      if (data.type === 'meta') {
        setStreaming(true)
        setMessages(prev => [...prev, { role: 'agent', content: '', intent: data.intent }])
      } else if (data.type === 'token') {
        setMessages(prev => {
          const updated = [...prev]
          const last = updated[updated.length - 1]
          if (last?.role === 'agent') {
            updated[updated.length - 1] = { ...last, content: last.content + data.content }
          }
          return updated
        })
      } else if (data.type === 'done') {
        setStreaming(false)
      }
    }

    wsRef.current = ws
  }

  function send() {
    const text = input.trim()
    if (!text || !wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return

    setMessages(prev => [...prev, { role: 'user', content: text }])
    wsRef.current.send(JSON.stringify({ message: text }))
    setInput('')
    setStreaming(true)
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
        <div className={`dot ${connected ? 'online' : 'offline'}`} />
        <h1>Porthon Agent</h1>
        <span className="status">{connected ? 'online' : 'reconnecting...'}</span>
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
            {msg.role === 'agent' && msg.intent && msg.intent !== 'casual' && (
              <span className="badge">{msg.intent}</span>
            )}
            <div className="content">{msg.content}</div>
          </div>
        ))}

        {streaming && messages[messages.length - 1]?.content === '' && (
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
          disabled={streaming}
        />
        <button onClick={send} disabled={streaming || !input.trim()}>
          Send
        </button>
      </div>
    </div>
  )
}

export default App
