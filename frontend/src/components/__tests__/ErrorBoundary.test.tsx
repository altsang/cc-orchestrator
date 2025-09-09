import React from 'react';
import { render, screen } from '@testing-library/react';
import { ErrorBoundary, DashboardErrorBoundary, WebSocketErrorBoundary } from '../ErrorBoundary';

// Mock logger
jest.mock('../../utils/logger', () => ({
  componentError: jest.fn(),
}));

// Mock environment
jest.mock('../../config/environment', () => ({
  environment: 'development',
}));

// Component that throws an error
const ThrowError: React.FC<{ shouldThrow?: boolean }> = ({ shouldThrow = true }) => {
  if (shouldThrow) {
    throw new Error('Test error');
  }
  return <div>Working component</div>;
};

describe('ErrorBoundary', () => {
  beforeEach(() => {
    // Suppress console errors for cleaner test output
    jest.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  it('renders children when no error occurs', () => {
    render(
      <ErrorBoundary>
        <ThrowError shouldThrow={false} />
      </ErrorBoundary>
    );

    expect(screen.getByText('Working component')).toBeInTheDocument();
  });

  it('renders error fallback UI when error occurs', () => {
    render(
      <ErrorBoundary>
        <ThrowError />
      </ErrorBoundary>
    );

    expect(screen.getByText('Something went wrong')).toBeInTheDocument();
    expect(screen.getByText(/We're sorry, but something unexpected happened/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Try Again' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Reload Page' })).toBeInTheDocument();
  });

  it('renders custom fallback when provided', () => {
    const customFallback = <div>Custom error message</div>;

    render(
      <ErrorBoundary fallback={customFallback}>
        <ThrowError />
      </ErrorBoundary>
    );

    expect(screen.getByText('Custom error message')).toBeInTheDocument();
  });

  it('calls onError callback when error occurs', () => {
    const mockOnError = jest.fn();

    render(
      <ErrorBoundary onError={mockOnError}>
        <ThrowError />
      </ErrorBoundary>
    );

    expect(mockOnError).toHaveBeenCalledWith(
      expect.any(Error),
      expect.objectContaining({
        componentStack: expect.any(String),
      })
    );
  });

  it('recovers from error when Try Again is clicked', () => {
    const { rerender } = render(
      <ErrorBoundary>
        <ThrowError />
      </ErrorBoundary>
    );

    expect(screen.getByText('Something went wrong')).toBeInTheDocument();

    const tryAgainButton = screen.getByRole('button', { name: 'Try Again' });
    tryAgainButton.click();

    // Re-render with a working component
    rerender(
      <ErrorBoundary>
        <ThrowError shouldThrow={false} />
      </ErrorBoundary>
    );

    expect(screen.getByText('Working component')).toBeInTheDocument();
  });
});

describe('DashboardErrorBoundary', () => {
  beforeEach(() => {
    jest.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  it('renders dashboard-specific error fallback', () => {
    render(
      <DashboardErrorBoundary>
        <ThrowError />
      </DashboardErrorBoundary>
    );

    expect(screen.getByText('Dashboard Error')).toBeInTheDocument();
    expect(screen.getByText(/There was a problem loading the dashboard/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Reload Dashboard' })).toBeInTheDocument();
  });
});

describe('WebSocketErrorBoundary', () => {
  beforeEach(() => {
    jest.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  it('renders websocket-specific error fallback', () => {
    render(
      <WebSocketErrorBoundary>
        <ThrowError />
      </WebSocketErrorBoundary>
    );

    expect(screen.getByText('Real-time Connection Error')).toBeInTheDocument();
    expect(screen.getByText(/The real-time connection encountered an error/)).toBeInTheDocument();
  });
});
