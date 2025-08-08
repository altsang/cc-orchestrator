import React from 'react';
import { render, screen } from '@testing-library/react';
import App from '../App';

// Mock the Dashboard component
jest.mock('../components/Dashboard', () => {
  return {
    Dashboard: () => <div data-testid="dashboard">Dashboard Component</div>,
  };
});

// Mock ErrorBoundary components
jest.mock('../components/ErrorBoundary', () => ({
  ErrorBoundary: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="error-boundary">{children}</div>
  ),
  DashboardErrorBoundary: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="dashboard-error-boundary">{children}</div>
  ),
}));

// Mock react-hot-toast
jest.mock('react-hot-toast', () => ({
  Toaster: () => <div data-testid="toaster">Toaster Component</div>,
}));

describe('App', () => {
  it('renders without crashing', () => {
    render(<App />);
    expect(screen.getByTestId('error-boundary')).toBeInTheDocument();
    expect(screen.getByTestId('dashboard-error-boundary')).toBeInTheDocument();
    expect(screen.getByTestId('dashboard')).toBeInTheDocument();
    expect(screen.getByTestId('toaster')).toBeInTheDocument();
  });

  it('wraps Dashboard with error boundaries', () => {
    render(<App />);
    
    const errorBoundary = screen.getByTestId('error-boundary');
    const dashboardErrorBoundary = screen.getByTestId('dashboard-error-boundary');
    const dashboard = screen.getByTestId('dashboard');
    
    expect(errorBoundary).toContainElement(dashboardErrorBoundary);
    expect(dashboardErrorBoundary).toContainElement(dashboard);
  });

  it('includes Toaster component for notifications', () => {
    render(<App />);
    
    expect(screen.getByTestId('toaster')).toBeInTheDocument();
  });

  it('has correct app structure', () => {
    render(<App />);
    
    const appDiv = screen.getByTestId('error-boundary').firstChild as HTMLElement;
    expect(appDiv).toHaveClass('App');
  });
});