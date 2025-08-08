import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { TaskCard } from '../TaskCard';
import { Task, TaskStatus, TaskPriority } from '../../types';

const mockTask: Task = {
  id: 1,
  task_id: 'TASK-123',
  title: 'Test Task',
  description: 'This is a test task',
  status: TaskStatus.PENDING,
  priority: TaskPriority.HIGH,
  assigned_instance_id: null,
  created_at: '2023-01-01T00:00:00Z',
  updated_at: '2023-01-01T01:00:00Z',
  due_date: '2023-01-02T00:00:00Z',
  metadata: {
    estimated_duration: '2h',
    tags: ['frontend', 'bug'],
  },
};

const mockRunningTask: Task = {
  ...mockTask,
  status: TaskStatus.RUNNING,
  assigned_instance_id: 'instance-123',
};

describe('TaskCard', () => {
  it('renders task information correctly', () => {
    render(
      <TaskCard
        task={mockTask}
        onStart={jest.fn()}
        onComplete={jest.fn()}
        onCancel={jest.fn()}
        onAssign={jest.fn()}
      />
    );

    expect(screen.getByText('Test Task')).toBeInTheDocument();
    expect(screen.getByText('TASK-123')).toBeInTheDocument();
    expect(screen.getByText('This is a test task')).toBeInTheDocument();
  });

  it('displays correct status badge', () => {
    render(
      <TaskCard
        task={mockTask}
        onStart={jest.fn()}
        onComplete={jest.fn()}
        onCancel={jest.fn()}
        onAssign={jest.fn()}
      />
    );

    expect(screen.getByText('pending')).toBeInTheDocument();
  });

  it('displays priority badge', () => {
    render(
      <TaskCard
        task={mockTask}
        onStart={jest.fn()}
        onComplete={jest.fn()}
        onCancel={jest.fn()}
        onAssign={jest.fn()}
      />
    );

    expect(screen.getByText('high')).toBeInTheDocument();
  });

  it('shows start button for pending task', () => {
    render(
      <TaskCard
        task={mockTask}
        onStart={jest.fn()}
        onComplete={jest.fn()}
        onCancel={jest.fn()}
        onAssign={jest.fn()}
      />
    );

    expect(screen.getByRole('button', { name: /start/i })).toBeInTheDocument();
  });

  it('shows complete and cancel buttons for running task', () => {
    render(
      <TaskCard
        task={mockRunningTask}
        onStart={jest.fn()}
        onComplete={jest.fn()}
        onCancel={jest.fn()}
        onAssign={jest.fn()}
      />
    );

    expect(screen.getByRole('button', { name: /complete/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument();
  });

  it('calls onStart when start button is clicked', () => {
    const mockOnStart = jest.fn();
    
    render(
      <TaskCard
        task={mockTask}
        onStart={mockOnStart}
        onComplete={jest.fn()}
        onCancel={jest.fn()}
        onAssign={jest.fn()}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: /start/i }));
    expect(mockOnStart).toHaveBeenCalledWith(mockTask.id);
  });

  it('calls onComplete when complete button is clicked', () => {
    const mockOnComplete = jest.fn();
    
    render(
      <TaskCard
        task={mockRunningTask}
        onStart={jest.fn()}
        onComplete={mockOnComplete}
        onCancel={jest.fn()}
        onAssign={jest.fn()}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: /complete/i }));
    expect(mockOnComplete).toHaveBeenCalledWith(mockRunningTask.id);
  });

  it('calls onCancel when cancel button is clicked', () => {
    const mockOnCancel = jest.fn();
    
    render(
      <TaskCard
        task={mockRunningTask}
        onStart={jest.fn()}
        onComplete={jest.fn()}
        onCancel={mockOnCancel}
        onAssign={jest.fn()}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: /cancel/i }));
    expect(mockOnCancel).toHaveBeenCalledWith(mockRunningTask.id);
  });

  it('displays metadata information', () => {
    render(
      <TaskCard
        task={mockTask}
        onStart={jest.fn()}
        onComplete={jest.fn()}
        onCancel={jest.fn()}
        onAssign={jest.fn()}
      />
    );

    expect(screen.getByText('2h')).toBeInTheDocument();
    expect(screen.getByText('frontend')).toBeInTheDocument();
    expect(screen.getByText('bug')).toBeInTheDocument();
  });

  it('shows due date when provided', () => {
    render(
      <TaskCard
        task={mockTask}
        onStart={jest.fn()}
        onComplete={jest.fn()}
        onCancel={jest.fn()}
        onAssign={jest.fn()}
      />
    );

    expect(screen.getByText(/Due:/)).toBeInTheDocument();
  });

  it('shows assigned instance when task is assigned', () => {
    render(
      <TaskCard
        task={mockRunningTask}
        onStart={jest.fn()}
        onComplete={jest.fn()}
        onCancel={jest.fn()}
        onAssign={jest.fn()}
      />
    );

    expect(screen.getByText(/Assigned to:/)).toBeInTheDocument();
    expect(screen.getByText('instance-123')).toBeInTheDocument();
  });
});