// Task card component for displaying task information

import React, { useState } from 'react';
import { StatusBadge } from './StatusBadge';
import { TaskCardProps, TaskPriority } from '../types';

const priorityColors = {
  low: 'text-blue-600 bg-blue-100',
  medium: 'text-yellow-600 bg-yellow-100',
  high: 'text-orange-600 bg-orange-100',
  critical: 'text-red-600 bg-red-100',
};

export const TaskCard: React.FC<TaskCardProps> = ({
  task,
  onStart,
  onComplete,
  onCancel,
  onAssign,
}) => {
  const [showAssignForm, setShowAssignForm] = useState(false);
  const [instanceId, setInstanceId] = useState('');

  const handleStart = () => onStart?.(task.id);
  const handleComplete = () => onComplete?.(task.id);
  const handleCancel = () => onCancel?.(task.id);
  
  const handleAssign = (e: React.FormEvent) => {
    e.preventDefault();
    const id = parseInt(instanceId);
    if (id && onAssign) {
      onAssign(task.id, id);
      setShowAssignForm(false);
      setInstanceId('');
    }
  };

  const canStart = task.status === 'pending' && task.instance_id;
  const canComplete = task.status === 'in_progress';
  const canCancel = task.status === 'pending' || task.status === 'in_progress';

  const priorityColor = priorityColors[task.priority] || priorityColors.medium;
  
  // Calculate duration display
  const getDurationDisplay = () => {
    if (task.status === 'completed' && task.actual_duration) {
      return `${task.actual_duration} min (actual)`;
    }
    if (task.estimated_duration) {
      return `${task.estimated_duration} min (est.)`;
    }
    return null;
  };

  const formatDate = (dateString?: string) => {
    return dateString ? new Date(dateString).toLocaleString() : null;
  };

  return (
    <div className="bg-white rounded-lg border border-gray-200 shadow-sm hover:shadow-md transition-shadow duration-200">
      <div className="p-6">
        {/* Header */}
        <div className="flex items-start justify-between mb-4">
          <div className="flex-1 min-w-0">
            <h3 className="text-lg font-semibold text-gray-900 truncate">
              {task.title}
            </h3>
            {task.description && (
              <p className="text-sm text-gray-600 mt-1 line-clamp-2">
                {task.description}
              </p>
            )}
          </div>
          <div className="flex flex-col items-end gap-2 ml-4">
            <StatusBadge status={task.status} size="sm" />
            <span className={`px-2 py-1 text-xs font-medium rounded-full ${priorityColor}`}>
              {task.priority.replace('_', ' ').toUpperCase()}
            </span>
          </div>
        </div>

        {/* Task Details */}
        <div className="space-y-2 mb-4">
          {task.instance_id && (
            <div className="text-sm">
              <span className="font-medium text-gray-700">Assigned to Instance:</span>
              <span className="ml-2 text-blue-600">#{task.instance_id}</span>
            </div>
          )}

          {task.worktree_id && (
            <div className="text-sm">
              <span className="font-medium text-gray-700">Worktree:</span>
              <span className="ml-2 text-blue-600">#{task.worktree_id}</span>
            </div>
          )}

          {task.due_date && (
            <div className="text-sm">
              <span className="font-medium text-gray-700">Due Date:</span>
              <span className="ml-2 text-gray-600">{formatDate(task.due_date)}</span>
            </div>
          )}

          {getDurationDisplay() && (
            <div className="text-sm">
              <span className="font-medium text-gray-700">Duration:</span>
              <span className="ml-2 text-gray-600">{getDurationDisplay()}</span>
            </div>
          )}

          {task.started_at && (
            <div className="text-sm">
              <span className="font-medium text-gray-700">Started:</span>
              <span className="ml-2 text-gray-600">{formatDate(task.started_at)}</span>
            </div>
          )}

          {task.completed_at && (
            <div className="text-sm">
              <span className="font-medium text-gray-700">Completed:</span>
              <span className="ml-2 text-gray-600">{formatDate(task.completed_at)}</span>
            </div>
          )}
        </div>

        {/* Requirements */}
        {Object.keys(task.requirements).length > 0 && (
          <div className="bg-blue-50 rounded-lg p-3 mb-4">
            <h4 className="text-sm font-medium text-blue-900 mb-2">Requirements</h4>
            <div className="text-sm text-blue-800">
              {Object.entries(task.requirements).map(([key, value]) => (
                <div key={key} className="flex justify-between">
                  <span className="font-medium">{key}:</span>
                  <span>{typeof value === 'object' ? JSON.stringify(value) : String(value)}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Results */}
        {Object.keys(task.results).length > 0 && (
          <div className="bg-green-50 rounded-lg p-3 mb-4">
            <h4 className="text-sm font-medium text-green-900 mb-2">Results</h4>
            <pre className="text-xs text-green-800 overflow-auto max-h-32">
              {JSON.stringify(task.results, null, 2)}
            </pre>
          </div>
        )}

        {/* Assignment Form */}
        {showAssignForm && (
          <form onSubmit={handleAssign} className="bg-gray-50 rounded-lg p-3 mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Assign to Instance ID:
            </label>
            <div className="flex gap-2">
              <input
                type="number"
                value={instanceId}
                onChange={(e) => setInstanceId(e.target.value)}
                placeholder="Enter instance ID"
                className="flex-1 px-3 py-1 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                required
              />
              <button
                type="submit"
                className="px-3 py-1 bg-blue-600 text-white text-sm rounded-md hover:bg-blue-700 transition-colors"
              >
                Assign
              </button>
              <button
                type="button"
                onClick={() => setShowAssignForm(false)}
                className="px-3 py-1 bg-gray-300 text-gray-700 text-sm rounded-md hover:bg-gray-400 transition-colors"
              >
                Cancel
              </button>
            </div>
          </form>
        )}

        {/* Action Buttons */}
        <div className="flex flex-col sm:flex-row gap-2">
          <button
            onClick={handleStart}
            disabled={!canStart}
            className={`px-3 py-2 text-sm font-medium rounded-md transition-colors duration-200 ${
              canStart
                ? 'bg-green-600 hover:bg-green-700 text-white'
                : 'bg-gray-100 text-gray-400 cursor-not-allowed'
            }`}
          >
            Start
          </button>
          
          <button
            onClick={handleComplete}
            disabled={!canComplete}
            className={`px-3 py-2 text-sm font-medium rounded-md transition-colors duration-200 ${
              canComplete
                ? 'bg-blue-600 hover:bg-blue-700 text-white'
                : 'bg-gray-100 text-gray-400 cursor-not-allowed'
            }`}
          >
            Complete
          </button>
          
          <button
            onClick={handleCancel}
            disabled={!canCancel}
            className={`px-3 py-2 text-sm font-medium rounded-md transition-colors duration-200 ${
              canCancel
                ? 'bg-red-600 hover:bg-red-700 text-white'
                : 'bg-gray-100 text-gray-400 cursor-not-allowed'
            }`}
          >
            Cancel
          </button>

          {!task.instance_id && (
            <button
              onClick={() => setShowAssignForm(true)}
              className="px-3 py-2 text-sm font-medium text-purple-600 bg-purple-50 hover:bg-purple-100 rounded-md transition-colors duration-200"
            >
              Assign
            </button>
          )}
        </div>

        {/* Metadata */}
        {Object.keys(task.extra_metadata).length > 0 && (
          <details className="mt-4">
            <summary className="text-xs font-medium text-gray-500 cursor-pointer hover:text-gray-700">
              Additional Metadata
            </summary>
            <pre className="mt-2 text-xs text-gray-600 bg-gray-50 p-2 rounded overflow-auto max-h-32">
              {JSON.stringify(task.extra_metadata, null, 2)}
            </pre>
          </details>
        )}
      </div>

      {/* Footer */}
      <div className="bg-gray-50 px-6 py-3 border-t border-gray-200">
        <div className="flex justify-between items-center text-xs text-gray-500">
          <span>Task #{task.id}</span>
          <span>Updated: {formatDate(task.updated_at)}</span>
        </div>
      </div>
    </div>
  );
};