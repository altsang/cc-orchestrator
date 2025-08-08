import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { TaskCard } from '../TaskCard';
import { Task, TaskStatus, TaskPriority } from '../../types';

const mockTask: Task = {
  id: 1,
  title: 'Test Task',
  description: 'This is a test task',
  status: TaskStatus.PENDING,
  priority: TaskPriority.HIGH,
  created_at: '2023-01-01T00:00:00Z',
  updated_at: '2023-01-01T01:00:00Z',
  due_date: '2023-01-02T00:00:00Z',
  estimated_duration: 120,
  requirements: {},
  results: {},
  extra_metadata: {
    tags: ['frontend', 'bug'],
  },
};

const mockRunningTask: Task = {
  ...mockTask,
  status: TaskStatus.IN_PROGRESS,
  instance_id: 123,
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
    expect(screen.getByText('Task #1')).toBeInTheDocument();
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

    expect(screen.getByText('Pending')).toBeInTheDocument();
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

    expect(screen.getByText('HIGH')).toBeInTheDocument();
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
    const taskWithInstance = {
      ...mockTask,
      instance_id: 123,
    };

    render(
      <TaskCard
        task={taskWithInstance}
        onStart={mockOnStart}
        onComplete={jest.fn()}
        onCancel={jest.fn()}
        onAssign={jest.fn()}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: /start/i }));
    expect(mockOnStart).toHaveBeenCalledWith(taskWithInstance.id);
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

    expect(screen.getByText('120 min (est.)')).toBeInTheDocument();
    // Tags are rendered as JSON in additional metadata
    expect(screen.getByText('Additional Metadata')).toBeInTheDocument();
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

    expect(screen.getByText('Due Date:')).toBeInTheDocument();
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

    expect(screen.getByText('Assigned to Instance:')).toBeInTheDocument();
    expect(screen.getByText('#123')).toBeInTheDocument();
  });

  it('shows actual duration for completed tasks', () => {
    const completedTask = {
      ...mockTask,
      status: TaskStatus.COMPLETED,
      actual_duration: 45,
    };

    render(
      <TaskCard
        task={completedTask}
        onStart={jest.fn()}
        onComplete={jest.fn()}
        onCancel={jest.fn()}
        onAssign={jest.fn()}
      />
    );

    expect(screen.getByText('45 min (actual)')).toBeInTheDocument();
  });

  it('shows assign form when task is not assigned', () => {
    const unassignedTask = {
      ...mockTask,
      instance_id: undefined,
    };

    render(
      <TaskCard
        task={unassignedTask}
        onStart={jest.fn()}
        onComplete={jest.fn()}
        onCancel={jest.fn()}
        onAssign={jest.fn()}
      />
    );

    expect(screen.getByText('Assign')).toBeInTheDocument();
  });

  it('handles assignment form submission', () => {
    const mockOnAssign = jest.fn();
    const unassignedTask = {
      ...mockTask,
      instance_id: undefined,
    };

    render(
      <TaskCard
        task={unassignedTask}
        onStart={jest.fn()}
        onComplete={jest.fn()}
        onCancel={jest.fn()}
        onAssign={mockOnAssign}
      />
    );

    // Click assign button to show form
    fireEvent.click(screen.getByText('Assign'));

    // Fill in instance ID
    const input = screen.getByRole('spinbutton');
    fireEvent.change(input, { target: { value: '456' } });

    // Submit form - there are multiple "Assign" buttons, get the one in the form
    const formAssignButton = screen.getAllByText('Assign')[0]; // The first one should be in the form
    fireEvent.click(formAssignButton);

    expect(mockOnAssign).toHaveBeenCalledWith(mockTask.id, 456);
  });

  it('shows worktree ID when provided', () => {
    const taskWithWorktree = {
      ...mockTask,
      worktree_id: 789,
    };

    render(
      <TaskCard
        task={taskWithWorktree}
        onStart={jest.fn()}
        onComplete={jest.fn()}
        onCancel={jest.fn()}
        onAssign={jest.fn()}
      />
    );

    expect(screen.getByText('Worktree:')).toBeInTheDocument();
    expect(screen.getByText('#789')).toBeInTheDocument();
  });

  it('shows task requirements when provided', () => {
    const taskWithRequirements = {
      ...mockTask,
      requirements: {
        memory: '4GB',
        cpu: '2 cores',
      },
    };

    render(
      <TaskCard
        task={taskWithRequirements}
        onStart={jest.fn()}
        onComplete={jest.fn()}
        onCancel={jest.fn()}
        onAssign={jest.fn()}
      />
    );

    expect(screen.getByText('Requirements')).toBeInTheDocument();
  });

  it('shows task results when completed', () => {
    const taskWithResults = {
      ...mockTask,
      status: TaskStatus.COMPLETED,
      results: {
        output: 'Success',
        exitCode: 0,
      },
    };

    render(
      <TaskCard
        task={taskWithResults}
        onStart={jest.fn()}
        onComplete={jest.fn()}
        onCancel={jest.fn()}
        onAssign={jest.fn()}
      />
    );

    expect(screen.getByText('Results')).toBeInTheDocument();
  });

  it('shows started_at timestamp when task has started', () => {
    const startedTask = {
      ...mockTask,
      status: TaskStatus.IN_PROGRESS,
      started_at: '2023-01-01T02:00:00Z',
    };

    render(
      <TaskCard
        task={startedTask}
        onStart={jest.fn()}
        onComplete={jest.fn()}
        onCancel={jest.fn()}
        onAssign={jest.fn()}
      />
    );

    expect(screen.getByText('Started:')).toBeInTheDocument();
  });

  it('shows completed_at timestamp when task is completed', () => {
    const completedTask = {
      ...mockTask,
      status: TaskStatus.COMPLETED,
      completed_at: '2023-01-01T03:00:00Z',
    };

    render(
      <TaskCard
        task={completedTask}
        onStart={jest.fn()}
        onComplete={jest.fn()}
        onCancel={jest.fn()}
        onAssign={jest.fn()}
      />
    );

    expect(screen.getByText('Completed:')).toBeInTheDocument();
  });
});
