import React from 'react';
import { render, screen } from '@testing-library/react';
import { ErrorMessage } from '../ErrorMessage';

describe('ErrorMessage', () => {
  it('renders error message correctly', () => {
    const errorMessage = 'Something went wrong';
    render(<ErrorMessage message={errorMessage} />);

    expect(screen.getByText(errorMessage)).toBeInTheDocument();
  });

  it('applies correct error styling', () => {
    render(<ErrorMessage message="Error text" />);

    const errorElement = screen.getByText('Error text');
    expect(errorElement).toHaveClass('text-red-600');
  });

  it('renders with proper accessibility attributes', () => {
    render(<ErrorMessage message="Error occurred" />);

    const errorElement = screen.getByRole('alert');
    expect(errorElement).toBeInTheDocument();
    expect(errorElement).toHaveTextContent('Error occurred');
  });

  it('handles empty message gracefully', () => {
    render(<ErrorMessage message="" />);

    const errorElement = screen.getByRole('alert');
    expect(errorElement).toBeInTheDocument();
    expect(errorElement).toHaveTextContent('');
  });
});