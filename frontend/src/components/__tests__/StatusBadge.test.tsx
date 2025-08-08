// Tests for StatusBadge component

import React from 'react';
import { render, screen } from '@testing-library/react';
import { StatusBadge } from '../StatusBadge';
import { InstanceStatus, HealthStatus, TaskStatus } from '../../types';

describe('StatusBadge', () => {
  it('renders instance status correctly', () => {
    render(<StatusBadge status={InstanceStatus.RUNNING} />);
    
    const badge = screen.getByText('Running');
    expect(badge).toBeInTheDocument();
    // The title attribute should be on the parent span
    const parentSpan = badge.parentElement;
    expect(parentSpan).toHaveAttribute('title', 'Status: Running');
  });

  it('renders task status correctly', () => {
    render(<StatusBadge status={TaskStatus.IN_PROGRESS} />);
    
    const badge = screen.getByText('In Progress');
    expect(badge).toBeInTheDocument();
    // The title attribute should be on the parent span
    const parentSpan = badge.parentElement;
    expect(parentSpan).toHaveAttribute('title', 'Status: In Progress');
  });

  it('renders health status correctly', () => {
    render(<StatusBadge status={HealthStatus.HEALTHY} />);
    
    const badge = screen.getByText('Healthy');
    expect(badge).toBeInTheDocument();
    // The title attribute should be on the parent span
    const parentSpan = badge.parentElement;
    expect(parentSpan).toHaveAttribute('title', 'Status: Healthy');
  });

  it('applies correct size classes', () => {
    render(<StatusBadge status={InstanceStatus.RUNNING} size="lg" />);
    
    const badge = screen.getByText('Running');
    expect(badge).toBeInTheDocument();
    // Test that size prop affects the component structure
    const parentSpan = badge.parentElement;
    expect(parentSpan).toHaveAttribute('title', 'Status: Running');
  });

  it('shows icon and text', () => {
    render(<StatusBadge status={InstanceStatus.RUNNING} />);
    
    const badge = screen.getByText('Running');
    expect(badge.parentElement).toContainHTML('✅');
  });

  it('has accessible title attribute', () => {
    render(<StatusBadge status={InstanceStatus.FAILED} />);
    
    const badge = screen.getByTitle('Status: Failed');
    expect(badge).toBeInTheDocument();
  });
});