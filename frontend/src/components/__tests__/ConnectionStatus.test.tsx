import React from 'react';
import { render, screen } from '@testing-library/react';
import { ConnectionStatus } from '../ConnectionStatus';

describe('ConnectionStatus', () => {
  it('renders connected status correctly', () => {
    render(<ConnectionStatus isConnected={true} />);

    expect(screen.getByText('Connected')).toBeInTheDocument();
    expect(screen.getByRole('status')).toHaveClass('text-green-600');
  });

  it('renders disconnected status correctly', () => {
    render(<ConnectionStatus isConnected={false} />);

    expect(screen.getByText('Disconnected')).toBeInTheDocument();
    expect(screen.getByRole('status')).toHaveClass('text-red-600');
  });

  it('shows connection indicator icon when connected', () => {
    render(<ConnectionStatus isConnected={true} />);

    const indicator = screen.getByRole('status');
    expect(indicator).toContainHTML('rounded-full');
  });

  it('shows disconnection indicator icon when disconnected', () => {
    render(<ConnectionStatus isConnected={false} />);

    const indicator = screen.getByRole('status');
    expect(indicator).toContainHTML('rounded-full');
  });

  it('applies correct styling based on connection state', () => {
    const { rerender } = render(<ConnectionStatus isConnected={true} />);

    let statusElement = screen.getByRole('status');
    expect(statusElement).toHaveClass('text-green-600');

    rerender(<ConnectionStatus isConnected={false} />);

    statusElement = screen.getByRole('status');
    expect(statusElement).toHaveClass('text-red-600');
  });
});
