import React from 'react';
import { Toaster } from 'react-hot-toast';
import { Dashboard } from './components/Dashboard';
import { ErrorBoundary, DashboardErrorBoundary } from './components/ErrorBoundary';

function App() {
  return (
    <ErrorBoundary>
      <div className="App">
        <DashboardErrorBoundary>
          <Dashboard />
        </DashboardErrorBoundary>
        <Toaster
        position="top-right"
        toastOptions={{
          duration: 4000,
          style: {
            background: '#363636',
            color: '#fff',
          },
          success: {
            duration: 3000,
            iconTheme: {
              primary: '#10b981',
              secondary: '#fff',
            },
          },
          error: {
            duration: 5000,
            iconTheme: {
              primary: '#ef4444',
              secondary: '#fff',
            },
          },
        }}
        />
      </div>
    </ErrorBoundary>
  );
}

export default App;
