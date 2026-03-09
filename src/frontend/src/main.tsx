import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import './index.css'
import App from './App.tsx'
import { AgentStreamProvider } from './contexts/AgentStreamContext.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <AgentStreamProvider>
        <App />
      </AgentStreamProvider>
    </BrowserRouter>
  </StrictMode>,
)
