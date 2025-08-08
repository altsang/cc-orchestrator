// Instance card component for displaying Claude instance information

import React from 'react';
import { StatusBadge } from './StatusBadge';
import { InstanceCardProps } from '../types';

export const InstanceCard: React.FC<InstanceCardProps> = ({
  instance,
  onStart,
  onStop,
  onViewDetails,
}) => {
  const handleStart = () => onStart?.(instance.id);
  const handleStop = () => onStop?.(instance.id);
  const handleViewDetails = () => onViewDetails?.(instance.id);

  const canStart = instance.status === 'stopped' || instance.status === 'failed';
  const canStop = instance.status === 'running' || instance.status === 'initializing';

  return (
    <div className="bg-white rounded-lg border border-gray-200 shadow-sm hover:shadow-md transition-shadow duration-200">
      <div className="p-6">
        {/* Header */}
        <div className="flex items-start justify-between mb-4">
          <div>
            <h3 className="text-lg font-semibold text-gray-900">
              Issue #{instance.issue_id}
            </h3>
            {instance.branch_name && (
              <p className="text-sm text-gray-500 mt-1">
                Branch: <code className="bg-gray-100 px-1 py-0.5 rounded text-xs">{instance.branch_name}</code>
              </p>
            )}
          </div>
          <div className="flex flex-col items-end gap-2">
            <StatusBadge status={instance.status} size="sm" />
            <StatusBadge status={instance.health_status} size="sm" />
          </div>
        </div>

        {/* Instance Details */}
        <div className="space-y-2 mb-4">
          {instance.workspace_path && (
            <div className="text-sm">
              <span className="font-medium text-gray-700">Workspace:</span>
              <code className="ml-2 bg-gray-100 px-1 py-0.5 rounded text-xs">{instance.workspace_path}</code>
            </div>
          )}

          {instance.tmux_session && (
            <div className="text-sm">
              <span className="font-medium text-gray-700">Tmux Session:</span>
              <code className="ml-2 bg-gray-100 px-1 py-0.5 rounded text-xs">{instance.tmux_session}</code>
            </div>
          )}

          {instance.process_id && (
            <div className="text-sm">
              <span className="font-medium text-gray-700">PID:</span>
              <code className="ml-2 bg-gray-100 px-1 py-0.5 rounded text-xs">{instance.process_id}</code>
            </div>
          )}

          {instance.last_activity && (
            <div className="text-sm text-gray-600">
              <span className="font-medium">Last Activity:</span>
              <span className="ml-2">{new Date(instance.last_activity).toLocaleString()}</span>
            </div>
          )}
        </div>

        {/* Health Information */}
        <div className="bg-gray-50 rounded-lg p-3 mb-4">
          <div className="flex justify-between items-center text-sm">
            <span className="font-medium text-gray-700">Health Checks</span>
            <span className="text-gray-600">
              {instance.healthy_check_count}/{instance.health_check_count}
            </span>
          </div>

          {instance.last_health_check && (
            <div className="text-xs text-gray-500 mt-1">
              Last check: {new Date(instance.last_health_check).toLocaleString()}
            </div>
          )}

          {instance.recovery_attempt_count > 0 && (
            <div className="text-xs text-yellow-600 mt-1">
              Recovery attempts: {instance.recovery_attempt_count}
            </div>
          )}
        </div>

        {/* Action Buttons */}
        <div className="flex flex-col sm:flex-row gap-2">
          <button
            onClick={handleStart}
            disabled={!canStart}
            className={`flex-1 px-3 py-2 text-sm font-medium rounded-md transition-colors duration-200 ${
              canStart
                ? 'bg-green-600 hover:bg-green-700 text-white'
                : 'bg-gray-100 text-gray-400 cursor-not-allowed'
            }`}
          >
            Start
          </button>

          <button
            onClick={handleStop}
            disabled={!canStop}
            className={`flex-1 px-3 py-2 text-sm font-medium rounded-md transition-colors duration-200 ${
              canStop
                ? 'bg-red-600 hover:bg-red-700 text-white'
                : 'bg-gray-100 text-gray-400 cursor-not-allowed'
            }`}
          >
            Stop
          </button>

          <button
            onClick={handleViewDetails}
            className="flex-1 sm:flex-initial px-3 py-2 text-sm font-medium text-blue-600 bg-blue-50 hover:bg-blue-100 rounded-md transition-colors duration-200"
          >
            Details
          </button>
        </div>

        {/* Metadata */}
        {Object.keys(instance.extra_metadata).length > 0 && (
          <details className="mt-4">
            <summary className="text-xs font-medium text-gray-500 cursor-pointer hover:text-gray-700">
              Additional Metadata
            </summary>
            <pre className="mt-2 text-xs text-gray-600 bg-gray-50 p-2 rounded overflow-auto max-h-32">
              {JSON.stringify(instance.extra_metadata, null, 2)}
            </pre>
          </details>
        )}
      </div>

      {/* Footer */}
      <div className="bg-gray-50 px-6 py-3 border-t border-gray-200">
        <div className="flex justify-between items-center text-xs text-gray-500">
          <span>ID: {instance.id}</span>
          <span>Updated: {new Date(instance.updated_at).toLocaleString()}</span>
        </div>
      </div>
    </div>
  );
};
