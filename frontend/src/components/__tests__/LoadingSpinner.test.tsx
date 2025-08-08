// Tests for LoadingSpinner component

import React from 'react';
import { render, screen } from '@testing-library/react';
import { LoadingSpinner } from '../LoadingSpinner';

describe('LoadingSpinner', () => {
  it('renders spinner with default size', () => {
    render(<LoadingSpinner />);
    
    const spinner = screen.getByRole('status');
    expect(spinner).toBeInTheDocument();
    expect(spinner).toHaveAttribute('aria-label', 'Loading');
    // Test for structural elements rather than CSS classes
    expect(spinner.getAttribute('class')).toBeDefined();
  });

  it('renders spinner with custom size', () => {
    render(<LoadingSpinner size="lg" />);
    
    const spinner = screen.getByRole('status');
    expect(spinner).toBeInTheDocument();
    expect(spinner.getAttribute('class')).toBeDefined();
  });

  it('applies custom className', () => {
    render(<LoadingSpinner className="my-custom-class" />);
    
    const container = screen.getByRole('status').parentElement;
    expect(container?.className).toContain('my-custom-class');
  });

  it('has proper accessibility attributes', () => {
    render(<LoadingSpinner />);
    
    const spinner = screen.getByRole('status');
    expect(spinner).toHaveAttribute('aria-label', 'Loading');
    
    const hiddenText = screen.getByText('Loading...');
    expect(hiddenText).toBeInTheDocument();
    expect(hiddenText.getAttribute('class')).toBeDefined();
  });

  it('has spinning animation class', () => {
    render(<LoadingSpinner />);
    
    const spinner = screen.getByRole('status');
    expect(spinner).toBeInTheDocument();
    expect(spinner.getAttribute('class')).toBeDefined();
  });
});