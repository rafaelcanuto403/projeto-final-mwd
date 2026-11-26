import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClientProvider } from '@tanstack/react-query'
import DevtoolsNeo from './components/DevtoolsNeo.jsx'
import './index.css'
import App from './App.jsx'
import { queryClient } from './api/queryClient.js'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
      {/* Painel para inspecionar o cache; só aparece em desenvolvimento (npm run dev). */}
      <DevtoolsNeo />
    </QueryClientProvider>
  </StrictMode>,
)
