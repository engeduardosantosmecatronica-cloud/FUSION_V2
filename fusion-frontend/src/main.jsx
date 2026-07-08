import React from 'react'
import ReactDOM from 'react-dom/client'
import App from '@/App.jsx'
import AppErrorBoundary from '@/components/AppErrorBoundary.jsx'
import '@/index.css'

window.addEventListener('error', event => {
  console.error('[Fusion Frontend fatal error]', event.error || event.message)
})
window.addEventListener('unhandledrejection', event => {
  console.error('[Fusion Frontend unhandled rejection]', event.reason)
})

ReactDOM.createRoot(document.getElementById('root')).render(
  <AppErrorBoundary>
    <App />
  </AppErrorBoundary>
)
