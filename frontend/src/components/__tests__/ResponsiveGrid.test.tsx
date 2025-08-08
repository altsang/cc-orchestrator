import React from 'react';
import { render, screen } from '@testing-library/react';
import { StatsGrid, InstanceGrid, TaskGrid } from '../ResponsiveGrid';

describe('ResponsiveGrid components', () => {
  describe('StatsGrid', () => {
    it('renders children in a responsive grid layout', () => {
      render(
        <StatsGrid>
          <div data-testid="child-1">Child 1</div>
          <div data-testid="child-2">Child 2</div>
          <div data-testid="child-3">Child 3</div>
        </StatsGrid>
      );

      const grid = screen.getByTestId('child-1').parentElement;
      expect(grid).toHaveClass(
        'grid',
        'grid-cols-1',
        'sm:grid-cols-2',
        'lg:grid-cols-3',
        'xl:grid-cols-4',
        'gap-4',
        'mb-6'
      );

      expect(screen.getByTestId('child-1')).toBeInTheDocument();
      expect(screen.getByTestId('child-2')).toBeInTheDocument();
      expect(screen.getByTestId('child-3')).toBeInTheDocument();
    });

    it('handles empty children', () => {
      render(<StatsGrid />);
      
      // Grid should still render even with no children
      const gridElement = document.querySelector('.grid');
      expect(gridElement).toBeInTheDocument();
    });

    it('handles single child', () => {
      render(
        <StatsGrid>
          <div data-testid="single-child">Only Child</div>
        </StatsGrid>
      );

      expect(screen.getByTestId('single-child')).toBeInTheDocument();
      const grid = screen.getByTestId('single-child').parentElement;
      expect(grid).toHaveClass('grid');
    });

    it('handles many children', () => {
      const children = Array.from({ length: 10 }, (_, i) => (
        <div key={i} data-testid={`child-${i}`}>Child {i}</div>
      ));

      render(<StatsGrid>{children}</StatsGrid>);

      children.forEach((_, i) => {
        expect(screen.getByTestId(`child-${i}`)).toBeInTheDocument();
      });
    });

    it('applies correct responsive breakpoints', () => {
      render(
        <StatsGrid>
          <div data-testid="test-child">Test</div>
        </StatsGrid>
      );

      const grid = screen.getByTestId('test-child').parentElement;
      expect(grid).toHaveClass('grid-cols-1'); // Mobile: 1 column
      expect(grid).toHaveClass('sm:grid-cols-2'); // Small: 2 columns
      expect(grid).toHaveClass('lg:grid-cols-3'); // Large: 3 columns
      expect(grid).toHaveClass('xl:grid-cols-4'); // XL: 4 columns
    });
  });

  describe('InstanceGrid', () => {
    it('renders children in instance grid layout', () => {
      render(
        <InstanceGrid>
          <div data-testid="instance-1">Instance 1</div>
          <div data-testid="instance-2">Instance 2</div>
        </InstanceGrid>
      );

      const grid = screen.getByTestId('instance-1').parentElement;
      expect(grid).toHaveClass(
        'grid',
        'grid-cols-1',
        'md:grid-cols-2',
        'lg:grid-cols-3',
        'gap-4'
      );

      expect(screen.getByTestId('instance-1')).toBeInTheDocument();
      expect(screen.getByTestId('instance-2')).toBeInTheDocument();
    });

    it('uses correct responsive breakpoints for instances', () => {
      render(
        <InstanceGrid>
          <div data-testid="test-instance">Test Instance</div>
        </InstanceGrid>
      );

      const grid = screen.getByTestId('test-instance').parentElement;
      expect(grid).toHaveClass('grid-cols-1'); // Mobile: 1 column
      expect(grid).toHaveClass('md:grid-cols-2'); // Medium: 2 columns
      expect(grid).toHaveClass('lg:grid-cols-3'); // Large: 3 columns
      expect(grid).not.toHaveClass('xl:grid-cols-4'); // No XL breakpoint
    });

    it('handles empty instances', () => {
      render(<InstanceGrid />);
      
      const gridElement = document.querySelector('.grid');
      expect(gridElement).toBeInTheDocument();
    });

    it('handles large number of instances', () => {
      const instances = Array.from({ length: 20 }, (_, i) => (
        <div key={i} data-testid={`instance-${i}`}>Instance {i}</div>
      ));

      render(<InstanceGrid>{instances}</InstanceGrid>);

      // Check first few and last few instances
      expect(screen.getByTestId('instance-0')).toBeInTheDocument();
      expect(screen.getByTestId('instance-19')).toBeInTheDocument();
    });
  });

  describe('TaskGrid', () => {
    it('renders children in task grid layout', () => {
      render(
        <TaskGrid>
          <div data-testid="task-1">Task 1</div>
          <div data-testid="task-2">Task 2</div>
          <div data-testid="task-3">Task 3</div>
        </TaskGrid>
      );

      const grid = screen.getByTestId('task-1').parentElement;
      expect(grid).toHaveClass(
        'grid',
        'grid-cols-1',
        'sm:grid-cols-2',
        'lg:grid-cols-3',
        'xl:grid-cols-4',
        'gap-4'
      );

      expect(screen.getByTestId('task-1')).toBeInTheDocument();
      expect(screen.getByTestId('task-2')).toBeInTheDocument();
      expect(screen.getByTestId('task-3')).toBeInTheDocument();
    });

    it('uses same responsive breakpoints as StatsGrid', () => {
      render(
        <TaskGrid>
          <div data-testid="test-task">Test Task</div>
        </TaskGrid>
      );

      const grid = screen.getByTestId('test-task').parentElement;
      expect(grid).toHaveClass('grid-cols-1'); // Mobile: 1 column
      expect(grid).toHaveClass('sm:grid-cols-2'); // Small: 2 columns
      expect(grid).toHaveClass('lg:grid-cols-3'); // Large: 3 columns
      expect(grid).toHaveClass('xl:grid-cols-4'); // XL: 4 columns
    });

    it('handles empty tasks', () => {
      render(<TaskGrid />);
      
      const gridElement = document.querySelector('.grid');
      expect(gridElement).toBeInTheDocument();
    });

    it('handles mixed content types', () => {
      render(
        <TaskGrid>
          <div data-testid="text-task">Text Task</div>
          <button data-testid="button-task">Button Task</button>
          <span data-testid="span-task">Span Task</span>
        </TaskGrid>
      );

      expect(screen.getByTestId('text-task')).toBeInTheDocument();
      expect(screen.getByTestId('button-task')).toBeInTheDocument();
      expect(screen.getByTestId('span-task')).toBeInTheDocument();
    });

    it('preserves child component props', () => {
      render(
        <TaskGrid>
          <div data-testid="task-with-props" className="custom-class" id="custom-id">
            Task with props
          </div>
        </TaskGrid>
      );

      const task = screen.getByTestId('task-with-props');
      expect(task).toHaveClass('custom-class');
      expect(task).toHaveAttribute('id', 'custom-id');
    });
  });

  describe('Common grid behavior', () => {
    it('all grids use gap-4 for consistent spacing', () => {
      const { container: statsContainer } = render(
        <StatsGrid><div>Stats</div></StatsGrid>
      );
      const { container: instanceContainer } = render(
        <InstanceGrid><div>Instance</div></InstanceGrid>
      );
      const { container: taskContainer } = render(
        <TaskGrid><div>Task</div></TaskGrid>
      );

      const statsGrid = statsContainer.querySelector('.grid');
      const instanceGrid = instanceContainer.querySelector('.grid');
      const taskGrid = taskContainer.querySelector('.grid');

      expect(statsGrid).toHaveClass('gap-4');
      expect(instanceGrid).toHaveClass('gap-4');
      expect(taskGrid).toHaveClass('gap-4');
    });

    it('all grids are mobile-first responsive', () => {
      const { container: statsContainer } = render(
        <StatsGrid><div>Stats</div></StatsGrid>
      );
      const { container: instanceContainer } = render(
        <InstanceGrid><div>Instance</div></InstanceGrid>
      );
      const { container: taskContainer } = render(
        <TaskGrid><div>Task</div></TaskGrid>
      );

      const statsGrid = statsContainer.querySelector('.grid');
      const instanceGrid = instanceContainer.querySelector('.grid');
      const taskGrid = taskContainer.querySelector('.grid');

      // All should start with grid-cols-1 for mobile
      expect(statsGrid).toHaveClass('grid-cols-1');
      expect(instanceGrid).toHaveClass('grid-cols-1');
      expect(taskGrid).toHaveClass('grid-cols-1');
    });

    it('grids handle React fragments as children', () => {
      render(
        <StatsGrid>
          <>
            <div data-testid="fragment-child-1">Child 1</div>
            <div data-testid="fragment-child-2">Child 2</div>
          </>
        </StatsGrid>
      );

      expect(screen.getByTestId('fragment-child-1')).toBeInTheDocument();
      expect(screen.getByTestId('fragment-child-2')).toBeInTheDocument();
    });

    it('grids handle null and undefined children gracefully', () => {
      render(
        <StatsGrid>
          <div data-testid="valid-child">Valid</div>
          {null}
          {undefined}
          {false && <div>Hidden</div>}
        </StatsGrid>
      );

      expect(screen.getByTestId('valid-child')).toBeInTheDocument();
      // Null, undefined, and false conditions should be handled by React
    });
  });
});