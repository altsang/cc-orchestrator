import React from 'react'
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { WebSocketProvider } from './contexts/WebSocketContext'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import InstanceDetail from './pages/InstanceDetail'
import Logs from './pages/Logs'

function App() {
  return (
    <Router>
      <WebSocketProvider>
        <Layout>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/instances/:id" element={<InstanceDetail />} />
            <Route path="/logs" element={<Logs />} />
          </Routes>
        </Layout>
      </WebSocketProvider>
    </Router>
  )
}

export default App
