import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { InstanceCard } from '../InstanceCard';
import { Instance, InstanceStatus } from '../../types';

// Mock the hooks and services
jest.mock('../../hooks/useApi', () => ({
  useInstanceOperations: () => ({
    startInstance: jest.fn().mockResolvedValue(undefined),
    stopInstance: jest.fn().mockResolvedValue(undefined),
    isLoading: false,
  }),
}));

const mockInstance: Instance = {
  id: 1,
  instance_id: 'test-instance-1',
  issue_id: 'ISSUE-123',
  status: InstanceStatus.RUNNING,
  branch: 'feature/test-branch',
  workspace_path: '/workspace/test',
  created_at: '2023-01-01T00:00:00Z',
  updated_at: '2023-01-01T01:00:00Z',
  metadata: {
    last_active: '2023-01-01T01:00:00Z',
  },
};

const mockStoppedInstance: Instance = {
  ...mockInstance,
  status: InstanceStatus.STOPPED,
};

describe('InstanceCard', () => {
  it('renders instance information correctly', () => {
    render(
      <InstanceCard
        instance={mockInstance}
        onStart={jest.fn()}
        onStop={jest.fn()}
        onViewDetails={jest.fn()}
      />
    );

    expect(screen.getByText('ISSUE-123')).toBeInTheDocument();
    expect(screen.getByText('test-instance-1')).toBeInTheDocument();
    expect(screen.getByText('feature/test-branch')).toBeInTheDocument();
    expect(screen.getByText('/workspace/test')).toBeInTheDocument();
  });

  it('displays correct status badge for running instance', () => {
    render(
      <InstanceCard
        instance={mockInstance}
        onStart={jest.fn()}
        onStop={jest.fn()}
        onViewDetails={jest.fn()}
      />
    );

    expect(screen.getByText('running')).toBeInTheDocument();
  });

  it('shows start button for stopped instance', () => {
    render(
      <InstanceCard
        instance={mockStoppedInstance}
        onStart={jest.fn()}
        onStop={jest.fn()}
        onViewDetails={jest.fn()}
      />
    );

    expect(screen.getByRole('button', { name: /start/i })).toBeInTheDocument();
  });

  it('shows stop button for running instance', () => {
    render(
      <InstanceCard
        instance={mockInstance}
        onStart={jest.fn()}
        onStop={jest.fn()}
        onViewDetails={jest.fn()}
      />
    );

    expect(screen.getByRole('button', { name: /stop/i })).toBeInTheDocument();
  });

  it('calls onStart when start button is clicked', () => {
    const mockOnStart = jest.fn();
    
    render(
      <InstanceCard
        instance={mockStoppedInstance}
        onStart={mockOnStart}
        onStop={jest.fn()}
        onViewDetails={jest.fn()}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: /start/i }));
    expect(mockOnStart).toHaveBeenCalledWith(mockStoppedInstance.id);
  });

  it('calls onStop when stop button is clicked', () => {
    const mockOnStop = jest.fn();
    
    render(
      <InstanceCard
        instance={mockInstance}
        onStart={jest.fn()}
        onStop={mockOnStop}
        onViewDetails={jest.fn()}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: /stop/i }));
    expect(mockOnStop).toHaveBeenCalledWith(mockInstance.id);
  });

  it('calls onViewDetails when view details button is clicked', () => {
    const mockOnViewDetails = jest.fn();
    
    render(
      <InstanceCard
        instance={mockInstance}
        onStart={jest.fn()}
        onStop={jest.fn()}
        onViewDetails={mockOnViewDetails}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: /view details/i }));
    expect(mockOnViewDetails).toHaveBeenCalledWith(mockInstance.id);
  });

  it('displays timestamps correctly', () => {
    render(
      <InstanceCard
        instance={mockInstance}
        onStart={jest.fn()}
        onStop={jest.fn()}
        onViewDetails={jest.fn()}
      />
    );

    expect(screen.getByText(/Created:/)).toBeInTheDocument();
    expect(screen.getByText(/Updated:/)).toBeInTheDocument();
  });
});