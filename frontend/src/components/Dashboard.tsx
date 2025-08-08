// Main dashboard component for CC-Orchestrator

import React, { useState, useEffect, useMemo } from 'react';
import logger from '../utils/logger';
import { LoadingSpinner } from './LoadingSpinner';
import { ErrorMessage } from './ErrorMessage';
import { ConnectionStatus } from './ConnectionStatus';
import { InstanceCard } from './InstanceCard';
import { TaskCard } from './TaskCard';
import { StatusBadge } from './StatusBadge';
import { MobileMenu } from './MobileMenu';
import { StatsGrid, InstanceGrid, TaskGrid } from './ResponsiveGrid';
import { useDebouncedRefetchers } from '../hooks/useDebounce';
import {
  useInstances,
  useTasks,
  useInstanceOperations,
  useTaskOperations,
  useSystemStatus,
  useHealthOverview,
  useRecentCriticalAlerts
} from '../hooks/useApi';
import { useDashboardWebSocket } from '../hooks/useWebSocket';
import toast from 'react-hot-toast';
import type {
  WebSocketMessage,
  InstanceUpdate,
  TaskUpdate,
  AlertMessage,
  SystemStatusUpdate
} from '../types';

export const Dashboard: React.FC = () => {
  // State for filters and pagination
  const [instanceFilter, setInstanceFilter] = useState({
    page: 1,
    size: 12,
  });
  const [taskFilter, setTaskFilter] = useState({
    page: 1,
    size: 12,
  });
  const [activeTab, setActiveTab] = useState<'overview' | 'instances' | 'tasks'>('overview');

  // API hooks
  const {
    data: instancesData,
    loading: instancesLoading,
    error: instancesError,
    refetch: refetchInstances
  } = useInstances(instanceFilter.page, instanceFilter.size);

  const {
    data: tasksData,
    loading: tasksLoading,
    error: tasksError,
    refetch: refetchTasks
  } = useTasks(taskFilter.page, taskFilter.size);

  const {
    data: healthOverview,
    loading: healthLoading,
    refetch: refetchHealth
  } = useHealthOverview();

  const {
    data: criticalAlerts,
    refetch: refetchAlerts
  } = useRecentCriticalAlerts();

  const instanceOps = useInstanceOperations();
  const taskOps = useTaskOperations();
  const systemStatus = useSystemStatus();

  // Debounced refetchers to prevent excessive API calls from WebSocket messages
  const debouncedRefetchers = useDebouncedRefetchers({
    instances: refetchInstances,
    tasks: refetchTasks,
    health: refetchHealth,
    alerts: refetchAlerts,
  }, 1000); // 1 second debounce

  // WebSocket connection
  const websocket = useDashboardWebSocket((message: WebSocketMessage) => {
    logger.debug('Dashboard received WebSocket message', { type: message.type });

    switch (message.type) {
      case 'instance_update':
        const instanceUpdate = message as InstanceUpdate;
        toast.success(`Instance ${instanceUpdate.data.issue_id} status updated to ${instanceUpdate.data.status}`);
        debouncedRefetchers.instances();
        break;

      case 'task_update':
        const taskUpdate = message as TaskUpdate;
        toast.success(`Task "${taskUpdate.data.title}" status updated to ${taskUpdate.data.status}`);
        debouncedRefetchers.tasks();
        break;

      case 'alert':
        const alertMessage = message as AlertMessage;
        if (alertMessage.data.level === 'critical') {
          toast.error(`Critical Alert: ${alertMessage.data.message}`);
        } else if (alertMessage.data.level === 'error') {
          toast.error(`Error: ${alertMessage.data.message}`);
        } else {
          toast(`${alertMessage.data.level.toUpperCase()}: ${alertMessage.data.message}`);
        }
        debouncedRefetchers.alerts();
        break;

      case 'system_status':
        const statusUpdate = message as SystemStatusUpdate;
        if (statusUpdate.data.system_health === 'unhealthy') {
          toast.error('System health is unhealthy');
        }
        debouncedRefetchers.health();
        break;
    }
  });

  // Instance operations handlers
  const handleStartInstance = async (id: number) => {
    const result = await instanceOps.startInstance(id);
    if (result) {
      toast.success(`Instance ${result.issue_id} started successfully`);
      refetchInstances();
    }
  };

  const handleStopInstance = async (id: number) => {
    const result = await instanceOps.stopInstance(id);
    if (result) {
      toast.success(`Instance ${result.issue_id} stopped successfully`);
      refetchInstances();
    }
  };

  const handleViewInstanceDetails = (id: number) => {
    // TODO: Navigate to instance details page
    logger.debug('View details for instance', { instanceId: id });
  };

  // Task operations handlers
  const handleStartTask = async (id: number) => {
    const result = await taskOps.startTask(id);
    if (result) {
      toast.success(`Task "${result.title}" started successfully`);
      refetchTasks();
    }
  };

  const handleCompleteTask = async (id: number) => {
    const result = await taskOps.completeTask(id);
    if (result) {
      toast.success(`Task "${result.title}" completed successfully`);
      refetchTasks();
    }
  };

  const handleCancelTask = async (id: number) => {
    const result = await taskOps.cancelTask(id);
    if (result) {
      toast.success(`Task "${result.title}" cancelled`);
      refetchTasks();
    }
  };

  const handleAssignTask = async (taskId: number, instanceId: number) => {
    const result = await taskOps.assignTask(taskId, instanceId);
    if (result) {
      toast.success(`Task "${result.title}" assigned to instance ${instanceId}`);
      refetchTasks();
    }
  };

  // Statistics calculations
  const getSystemStats = () => {
    const instances = instancesData?.items || [];
    const tasks = tasksData?.items || [];

    return {
      totalInstances: instances.length,
      runningInstances: instances.filter(i => i.status === 'running').length,
      healthyInstances: instances.filter(i => i.health_status === 'healthy').length,
      totalTasks: tasks.length,
      pendingTasks: tasks.filter(t => t.status === 'pending').length,
      activeTasks: tasks.filter(t => t.status === 'in_progress').length,
      completedTasks: tasks.filter(t => t.status === 'completed').length,
    };
  };

  const stats = getSystemStats();

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center min-w-0 flex-1">
              <h1 className="text-xl sm:text-2xl font-bold text-gray-900 truncate">
                CC-Orchestrator
              </h1>
              <div className="ml-2 sm:ml-4 hidden sm:block">
                <ConnectionStatus
                  isConnected={websocket.isConnected}
                  className="text-sm"
                />
              </div>
            </div>

            <div className="flex items-center space-x-2 sm:space-x-4">
              {/* Mobile connection status */}
              <div className="sm:hidden">
                <div className={`w-3 h-3 rounded-full ${websocket.isConnected ? 'bg-green-500' : 'bg-red-500'}`}></div>
              </div>

              {/* Desktop status indicators */}
              <div className="hidden sm:flex items-center space-x-4">
                {systemStatus.isConnected ? (
                  <div className="flex items-center text-sm text-green-600">
                    <div className="w-2 h-2 bg-green-500 rounded-full mr-2"></div>
                    <span className="hidden md:inline">API Connected</span>
                  </div>
                ) : (
                  <div className="flex items-center text-sm text-red-600">
                    <div className="w-2 h-2 bg-red-500 rounded-full mr-2"></div>
                    <span className="hidden md:inline">API Disconnected</span>
                  </div>
                )}

                {criticalAlerts?.data && criticalAlerts.data.length > 0 && (
                  <div className="flex items-center text-sm text-red-600">
                    <svg className="w-4 h-4 mr-1" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                    </svg>
                    <span className="hidden md:inline">{criticalAlerts.data.length} Critical Alert{criticalAlerts.data.length > 1 ? 's' : ''}</span>
                    <span className="md:hidden">{criticalAlerts.data.length}</span>
                  </div>
                )}
              </div>

              {/* Mobile menu */}
              <MobileMenu activeTab={activeTab} onTabChange={setActiveTab} />
            </div>
          </div>
        </div>
      </header>

      {/* Navigation Tabs - Desktop Only */}
      <nav className="bg-white border-b border-gray-200 hidden lg:block">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex space-x-8">
            {[
              { key: 'overview', label: 'Overview', icon: '📊' },
              { key: 'instances', label: 'Instances', icon: '💻' },
              { key: 'tasks', label: 'Tasks', icon: '📋' },
            ].map((tab) => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key as any)}
                className={`py-4 px-1 border-b-2 font-medium text-sm flex items-center space-x-2 ${
                  activeTab === tab.key
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                <span>{tab.icon}</span>
                <span>{tab.label}</span>
              </button>
            ))}
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {activeTab === 'overview' && (
          <div className="space-y-8">
            {/* System Statistics */}
            <StatsGrid>
              <div className="bg-white rounded-lg p-6 shadow-sm border border-gray-200">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-600">Total Instances</p>
                    <p className="text-3xl font-bold text-gray-900">{stats.totalInstances}</p>
                  </div>
                  <div className="text-blue-600">
                    <svg className="w-8 h-8" fill="currentColor" viewBox="0 0 20 20">
                      <path d="M3 4a1 1 0 011-1h12a1 1 0 011 1v2a1 1 0 01-1 1H4a1 1 0 01-1-1V4zM3 10a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H4a1 1 0 01-1-1v-6zM14 9a1 1 0 00-1 1v6a1 1 0 001 1h2a1 1 0 001-1v-6a1 1 0 00-1-1h-2z" />
                    </svg>
                  </div>
                </div>
                <div className="mt-2">
                  <span className="text-sm text-green-600 font-medium">
                    {stats.runningInstances} running
                  </span>
                </div>
              </div>

              <div className="bg-white rounded-lg p-6 shadow-sm border border-gray-200">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-600">Health Status</p>
                    <p className="text-3xl font-bold text-gray-900">{stats.healthyInstances}</p>
                  </div>
                  <div className="text-green-600">
                    <svg className="w-8 h-8" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                    </svg>
                  </div>
                </div>
                <div className="mt-2">
                  <span className="text-sm text-gray-600">
                    {stats.healthyInstances} of {stats.totalInstances} healthy
                  </span>
                </div>
              </div>

              <div className="bg-white rounded-lg p-6 shadow-sm border border-gray-200">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-600">Active Tasks</p>
                    <p className="text-3xl font-bold text-gray-900">{stats.activeTasks}</p>
                  </div>
                  <div className="text-purple-600">
                    <svg className="w-8 h-8" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M6 2a1 1 0 00-1 1v1H4a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V6a2 2 0 00-2-2h-1V3a1 1 0 10-2 0v1H7V3a1 1 0 00-1-1zm0 5a1 1 0 000 2h8a1 1 0 100-2H6z" clipRule="evenodd" />
                    </svg>
                  </div>
                </div>
                <div className="mt-2">
                  <span className="text-sm text-blue-600 font-medium">
                    {stats.pendingTasks} pending
                  </span>
                </div>
              </div>

              <div className="bg-white rounded-lg p-6 shadow-sm border border-gray-200">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-600">Completed</p>
                    <p className="text-3xl font-bold text-gray-900">{stats.completedTasks}</p>
                  </div>
                  <div className="text-green-600">
                    <svg className="w-8 h-8" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                    </svg>
                  </div>
                </div>
                <div className="mt-2">
                  <span className="text-sm text-gray-600">
                    {((stats.completedTasks / stats.totalTasks) * 100 || 0).toFixed(1)}% completion rate
                  </span>
                </div>
              </div>
            </StatsGrid>

            {/* Recent Activity Preview */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
              {/* Recent Instances */}
              <div className="bg-white rounded-lg shadow-sm border border-gray-200">
                <div className="px-6 py-4 border-b border-gray-200">
                  <h3 className="text-lg font-medium text-gray-900">Recent Instances</h3>
                </div>
                <div className="p-6">
                  {instancesLoading ? (
                    <LoadingSpinner className="py-8" />
                  ) : instancesError ? (
                    <ErrorMessage message={instancesError} onRetry={refetchInstances} />
                  ) : (
                    <div className="space-y-4">
                      {instancesData?.items.slice(0, 3).map((instance) => (
                        <div key={instance.id} className="flex items-center justify-between">
                          <div>
                            <p className="font-medium text-gray-900">Issue #{instance.issue_id}</p>
                            <p className="text-sm text-gray-500">{instance.branch_name}</p>
                          </div>
                          <StatusBadge status={instance.status} size="sm" />
                        </div>
                      ))}
                      {instancesData?.items.length === 0 && (
                        <p className="text-gray-500 text-center py-4">No instances found</p>
                      )}
                    </div>
                  )}
                </div>
              </div>

              {/* Recent Tasks */}
              <div className="bg-white rounded-lg shadow-sm border border-gray-200">
                <div className="px-6 py-4 border-b border-gray-200">
                  <h3 className="text-lg font-medium text-gray-900">Recent Tasks</h3>
                </div>
                <div className="p-6">
                  {tasksLoading ? (
                    <LoadingSpinner className="py-8" />
                  ) : tasksError ? (
                    <ErrorMessage message={tasksError} onRetry={refetchTasks} />
                  ) : (
                    <div className="space-y-4">
                      {tasksData?.items.slice(0, 3).map((task) => (
                        <div key={task.id} className="flex items-center justify-between">
                          <div>
                            <p className="font-medium text-gray-900 truncate">{task.title}</p>
                            <p className="text-sm text-gray-500">Priority: {task.priority}</p>
                          </div>
                          <StatusBadge status={task.status} size="sm" />
                        </div>
                      ))}
                      {tasksData?.items.length === 0 && (
                        <p className="text-gray-500 text-center py-4">No tasks found</p>
                      )}
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'instances' && (
          <div>
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-2xl font-bold text-gray-900">Instances</h2>
              <button className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md text-sm font-medium transition-colors">
                Create Instance
              </button>
            </div>

            {instancesLoading ? (
              <LoadingSpinner className="py-12" />
            ) : instancesError ? (
              <ErrorMessage message={instancesError} onRetry={refetchInstances} />
            ) : (
              <InstanceGrid>
                {instancesData?.items.map((instance) => (
                  <InstanceCard
                    key={instance.id}
                    instance={instance}
                    onStart={handleStartInstance}
                    onStop={handleStopInstance}
                    onViewDetails={handleViewInstanceDetails}
                  />
                ))}
                {instancesData?.items.length === 0 && (
                  <div className="col-span-full text-center py-12">
                    <p className="text-gray-500 text-lg">No instances found</p>
                  </div>
                )}
              </InstanceGrid>
            )}
          </div>
        )}

        {activeTab === 'tasks' && (
          <div>
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-2xl font-bold text-gray-900">Tasks</h2>
              <button className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md text-sm font-medium transition-colors">
                Create Task
              </button>
            </div>

            {tasksLoading ? (
              <LoadingSpinner className="py-12" />
            ) : tasksError ? (
              <ErrorMessage message={tasksError} onRetry={refetchTasks} />
            ) : (
              <TaskGrid>
                {tasksData?.items.map((task) => (
                  <TaskCard
                    key={task.id}
                    task={task}
                    onStart={handleStartTask}
                    onComplete={handleCompleteTask}
                    onCancel={handleCancelTask}
                    onAssign={handleAssignTask}
                  />
                ))}
                {tasksData?.items.length === 0 && (
                  <div className="col-span-full text-center py-12">
                    <p className="text-gray-500 text-lg">No tasks found</p>
                  </div>
                )}
              </TaskGrid>
            )}
          </div>
        )}
      </main>
    </div>
  );
};
