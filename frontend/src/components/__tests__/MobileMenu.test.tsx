import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { MobileMenu } from '../MobileMenu';

describe('MobileMenu', () => {
  const mockTabs = [
    { id: 'overview', label: 'Overview', icon: 'home' },
    { id: 'instances', label: 'Instances', icon: 'server' },
    { id: 'tasks', label: 'Tasks', icon: 'clipboard' },
  ];

  it('renders mobile menu button when closed', () => {
    render(
      <MobileMenu
        tabs={mockTabs}
        activeTab="overview"
        onTabChange={jest.fn()}
        isOpen={false}
        onToggle={jest.fn()}
      />
    );

    expect(screen.getByRole('button', { name: /open menu/i })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /close menu/i })).not.toBeInTheDocument();
  });

  it('renders mobile menu with tabs when open', () => {
    render(
      <MobileMenu
        tabs={mockTabs}
        activeTab="overview"
        onTabChange={jest.fn()}
        isOpen={true}
        onToggle={jest.fn()}
      />
    );

    expect(screen.getByRole('button', { name: /close menu/i })).toBeInTheDocument();
    expect(screen.getByText('Overview')).toBeInTheDocument();
    expect(screen.getByText('Instances')).toBeInTheDocument();
    expect(screen.getByText('Tasks')).toBeInTheDocument();
  });

  it('calls onToggle when menu button is clicked', () => {
    const mockToggle = jest.fn();

    render(
      <MobileMenu
        tabs={mockTabs}
        activeTab="overview"
        onTabChange={jest.fn()}
        isOpen={false}
        onToggle={mockToggle}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: /open menu/i }));
    expect(mockToggle).toHaveBeenCalledTimes(1);
  });

  it('calls onTabChange when tab is clicked', () => {
    const mockTabChange = jest.fn();

    render(
      <MobileMenu
        tabs={mockTabs}
        activeTab="overview"
        onTabChange={mockTabChange}
        isOpen={true}
        onToggle={jest.fn()}
      />
    );

    fireEvent.click(screen.getByText('Instances'));
    expect(mockTabChange).toHaveBeenCalledWith('instances');
  });

  it('highlights active tab', () => {
    render(
      <MobileMenu
        tabs={mockTabs}
        activeTab="instances"
        onTabChange={jest.fn()}
        isOpen={true}
        onToggle={jest.fn()}
      />
    );

    const activeTab = screen.getByText('Instances').closest('button');
    const inactiveTab = screen.getByText('Overview').closest('button');

    expect(activeTab).toHaveClass('text-blue-600', 'bg-blue-50');
    expect(inactiveTab).toHaveClass('text-gray-600');
    expect(inactiveTab).not.toHaveClass('text-blue-600', 'bg-blue-50');
  });

  it('closes menu when close button is clicked', () => {
    const mockToggle = jest.fn();

    render(
      <MobileMenu
        tabs={mockTabs}
        activeTab="overview"
        onTabChange={jest.fn()}
        isOpen={true}
        onToggle={mockToggle}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: /close menu/i }));
    expect(mockToggle).toHaveBeenCalledTimes(1);
  });

  it('renders with different tab configurations', () => {
    const singleTab = [{ id: 'single', label: 'Single Tab', icon: 'home' }];

    render(
      <MobileMenu
        tabs={singleTab}
        activeTab="single"
        onTabChange={jest.fn()}
        isOpen={true}
        onToggle={jest.fn()}
      />
    );

    expect(screen.getByText('Single Tab')).toBeInTheDocument();
    expect(screen.queryByText('Overview')).not.toBeInTheDocument();
  });

  it('handles empty tabs array', () => {
    render(
      <MobileMenu
        tabs={[]}
        activeTab=""
        onTabChange={jest.fn()}
        isOpen={true}
        onToggle={jest.fn()}
      />
    );

    expect(screen.getByRole('button', { name: /close menu/i })).toBeInTheDocument();
    // Should render menu structure even with no tabs
  });

  it('applies correct accessibility attributes', () => {
    render(
      <MobileMenu
        tabs={mockTabs}
        activeTab="overview"
        onTabChange={jest.fn()}
        isOpen={false}
        onToggle={jest.fn()}
      />
    );

    const menuButton = screen.getByRole('button', { name: /open menu/i });
    expect(menuButton).toHaveAttribute('aria-expanded', 'false');
  });

  it('updates aria-expanded when menu is opened', () => {
    const { rerender } = render(
      <MobileMenu
        tabs={mockTabs}
        activeTab="overview"
        onTabChange={jest.fn()}
        isOpen={false}
        onToggle={jest.fn()}
      />
    );

    let menuButton = screen.getByRole('button');
    expect(menuButton).toHaveAttribute('aria-expanded', 'false');

    rerender(
      <MobileMenu
        tabs={mockTabs}
        activeTab="overview"
        onTabChange={jest.fn()}
        isOpen={true}
        onToggle={jest.fn()}
      />
    );

    menuButton = screen.getByRole('button');
    expect(menuButton).toHaveAttribute('aria-expanded', 'true');
  });

  it('handles tab selection correctly', () => {
    const mockTabChange = jest.fn();

    render(
      <MobileMenu
        tabs={mockTabs}
        activeTab="overview"
        onTabChange={mockTabChange}
        isOpen={true}
        onToggle={jest.fn()}
      />
    );

    // Click each tab and verify correct ID is passed
    fireEvent.click(screen.getByText('Overview'));
    expect(mockTabChange).toHaveBeenCalledWith('overview');

    fireEvent.click(screen.getByText('Instances'));
    expect(mockTabChange).toHaveBeenCalledWith('instances');

    fireEvent.click(screen.getByText('Tasks'));
    expect(mockTabChange).toHaveBeenCalledWith('tasks');
  });
});