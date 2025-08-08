// Responsive grid component for adaptive layouts

import React from 'react';

interface ResponsiveGridProps {
  children: React.ReactNode;
  className?: string;
  minItemWidth?: string;
  gap?: string;
}

export const ResponsiveGrid: React.FC<ResponsiveGridProps> = ({
  children,
  className = '',
  minItemWidth = '300px',
  gap = '1.5rem',
}) => {
  return (
    <div
      className={`grid ${className}`}
      style={{
        gridTemplateColumns: `repeat(auto-fill, minmax(${minItemWidth}, 1fr))`,
        gap,
      }}
    >
      {children}
    </div>
  );
};

// Pre-configured responsive grids
export const InstanceGrid: React.FC<{ children: React.ReactNode; className?: string }> = ({
  children,
  className = ''
}) => (
  <ResponsiveGrid
    minItemWidth="320px"
    gap="1.5rem"
    className={`grid-cols-1 md:grid-cols-2 lg:grid-cols-3 ${className}`}
  >
    {children}
  </ResponsiveGrid>
);

export const TaskGrid: React.FC<{ children: React.ReactNode; className?: string }> = ({
  children,
  className = ''
}) => (
  <ResponsiveGrid
    minItemWidth="400px"
    gap="1.5rem"
    className={`grid-cols-1 lg:grid-cols-2 ${className}`}
  >
    {children}
  </ResponsiveGrid>
);

export const StatsGrid: React.FC<{ children: React.ReactNode; className?: string }> = ({
  children,
  className = ''
}) => (
  <ResponsiveGrid
    minItemWidth="250px"
    gap="1.5rem"
    className={`grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 ${className}`}
  >
    {children}
  </ResponsiveGrid>
);
