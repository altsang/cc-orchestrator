// Status badge component for displaying various status types

import React from 'react';
import { StatusBadgeProps } from '../types';

const statusColors = {
  // Instance Status
  initializing: 'bg-yellow-100 text-yellow-800 border-yellow-200',
  running: 'bg-green-100 text-green-800 border-green-200',
  stopped: 'bg-gray-100 text-gray-800 border-gray-200',
  failed: 'bg-red-100 text-red-800 border-red-200',
  terminating: 'bg-orange-100 text-orange-800 border-orange-200',

  // Task Status
  pending: 'bg-blue-100 text-blue-800 border-blue-200',
  in_progress: 'bg-purple-100 text-purple-800 border-purple-200',
  completed: 'bg-green-100 text-green-800 border-green-200',
  cancelled: 'bg-gray-100 text-gray-800 border-gray-200',

  // Health Status
  healthy: 'bg-green-100 text-green-800 border-green-200',
  degraded: 'bg-yellow-100 text-yellow-800 border-yellow-200',
  unhealthy: 'bg-red-100 text-red-800 border-red-200',
  unknown: 'bg-gray-100 text-gray-800 border-gray-200',

  // Worktree Status
  active: 'bg-green-100 text-green-800 border-green-200',
  inactive: 'bg-gray-100 text-gray-800 border-gray-200',
  cleanup: 'bg-yellow-100 text-yellow-800 border-yellow-200',
  error: 'bg-red-100 text-red-800 border-red-200',
};

const statusIcons = {
  // Instance Status
  initializing: '⏳',
  running: '✅',
  stopped: '⏹️',
  failed: '❌',
  terminating: '🔄',

  // Task Status
  pending: '⏱️',
  in_progress: '🔄',
  completed: '✅',
  cancelled: '⏹️',

  // Health Status
  healthy: '💚',
  degraded: '⚠️',
  unhealthy: '❌',
  unknown: '❓',

  // Worktree Status
  active: '📁',
  inactive: '📂',
  cleanup: '🧹',
  error: '❌',
};

const sizeClasses = {
  sm: 'px-2 py-1 text-xs',
  md: 'px-2.5 py-1 text-sm',
  lg: 'px-3 py-1.5 text-base',
};

export const StatusBadge: React.FC<StatusBadgeProps> = ({
  status,
  size = 'md'
}) => {
  const colorClass = statusColors[status] || 'bg-gray-100 text-gray-800 border-gray-200';
  const sizeClass = sizeClasses[size];
  const icon = statusIcons[status] || '❓';

  // Format status text
  const displayText = status.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());

  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full border font-medium ${colorClass} ${sizeClass}`}
      title={`Status: ${displayText}`}
    >
      <span className="text-xs leading-none">{icon}</span>
      <span>{displayText}</span>
    </span>
  );
};
