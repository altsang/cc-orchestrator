import React from 'react'
import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { ArrowLeft, Activity, Clock, Settings, Terminal } from 'lucide-react'
import { apiClient } from '../services/api'
import InstanceControls from '../components/InstanceControls'
import StatusIndicator from '../components/StatusIndicator'
import ResourceChart from '../components/ResourceChart'

const InstanceDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>()
  const instanceId = id ? parseInt(id, 10) : null

  const { data: instance, isLoading, error } = useQuery({
    queryKey: ['instance', instanceId],
    queryFn: () => instanceId ? apiClient.getInstance(instanceId) : null,
    enabled: !!instanceId,
  })

  const { data: health } = useQuery({
    queryKey: ['instance-health', instanceId],
    queryFn: () => instanceId ? apiClient.getInstanceHealth(instanceId) : null,
    enabled: !!instanceId,
    refetchInterval: 5000,
  })

  if (isLoading) {
    return (
      <div className="animate-pulse">
        <div className="h-8 bg-gray-200 rounded w-1/4 mb-4"></div>
        <div className="space-y-4">
          <div className="h-32 bg-gray-200 rounded"></div>
          <div className="h-64 bg-gray-200 rounded"></div>
        </div>
      </div>
    )
  }

  if (error || !instance) {
    return (
      <div className="text-center py-12">
        <div className="mx-auto h-12 w-12 text-red-400">
          <svg fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.732-.833-2.5 0L4.268 18.5c-.77.833.192 2.5 1.732 2.5z" />
          </svg>
        </div>
        <h3 className="mt-2 text-sm font-medium text-gray-900">Instance not found</h3>
        <p className="mt-1 text-sm text-gray-500">
          The requested instance could not be found.
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center space-x-4">
        <button
          type="button"
          className="rounded-md p-2 text-gray-400 hover:text-gray-500 focus:outline-none focus:ring-2 focus:ring-primary-500"
          onClick={() => window.history.back()}
        >
          <ArrowLeft className="h-5 w-5" />
        </button>
        <div className="flex-1">
          <h1 className="text-2xl font-bold text-gray-900">
            Instance #{instance.id} - Issue #{instance.issue_id}
          </h1>
          <div className="mt-2 flex items-center space-x-4">
            <StatusIndicator status={instance.status} size="lg" />
            <span className="text-sm text-gray-500">
              Created {new Date(instance.created_at).toLocaleString()}
            </span>
          </div>
        </div>
        <InstanceControls instance={instance} />
      </div>

      {/* Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="card p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <Activity className="h-8 w-8 text-blue-500" />
            </div>
            <div className="ml-5">
              <h3 className="text-lg font-medium text-gray-900">Status</h3>
              <StatusIndicator status={instance.status} />
            </div>
          </div>
        </div>

        <div className="card p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <Clock className="h-8 w-8 text-green-500" />
            </div>
            <div className="ml-5">
              <h3 className="text-lg font-medium text-gray-900">Uptime</h3>
              <p className="text-2xl font-semibold text-gray-900">
                {health ? Math.floor(health.uptime_seconds / 3600) : 0}h
              </p>
            </div>
          </div>
        </div>

        <div className="card p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <Terminal className="h-8 w-8 text-purple-500" />
            </div>
            <div className="ml-5">
              <h3 className="text-lg font-medium text-gray-900">Last Activity</h3>
              <p className="text-sm text-gray-600">
                {health?.last_activity
                  ? new Date(health.last_activity).toLocaleString()
                  : 'No recent activity'}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Resource Usage */}
      <div className="space-y-4">
        <h2 className="text-xl font-semibold text-gray-900">Resource Usage</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="card p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-medium text-gray-900">CPU Usage</h3>
              <span className="text-2xl font-bold text-blue-600">
                {health?.cpu_usage.toFixed(1) || 0}%
              </span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                style={{ width: `${health?.cpu_usage || 0}%` }}
              />
            </div>
          </div>

          <div className="card p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-medium text-gray-900">Memory Usage</h3>
              <span className="text-2xl font-bold text-green-600">
                {health?.memory_usage.toFixed(1) || 0}%
              </span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className="bg-green-600 h-2 rounded-full transition-all duration-300"
                style={{ width: `${health?.memory_usage || 0}%` }}
              />
            </div>
          </div>
        </div>
      </div>

      {/* Configuration */}
      <div className="space-y-4">
        <h2 className="text-xl font-semibold text-gray-900">Configuration</h2>
        <div className="card p-6">
          <div className="flex items-center mb-4">
            <Settings className="h-5 w-5 text-gray-400 mr-2" />
            <h3 className="text-lg font-medium text-gray-900">Instance Config</h3>
          </div>
          <div className="bg-gray-50 p-4 rounded-md">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <dt className="text-sm font-medium text-gray-500">Issue ID</dt>
                <dd className="mt-1 text-sm text-gray-900">{instance.issue_id}</dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-gray-500">Instance ID</dt>
                <dd className="mt-1 text-sm text-gray-900">{instance.id}</dd>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Recent Activity */}
      <div className="space-y-4">
        <h2 className="text-xl font-semibold text-gray-900">Recent Activity</h2>
        <div className="card p-6">
          <div className="flow-root">
            <ul className="-mb-8">
              <li>
                <div className="relative pb-8">
                  <span className="absolute top-4 left-4 -ml-px h-full w-0.5 bg-gray-200" aria-hidden="true" />
                  <div className="relative flex space-x-3">
                    <div>
                      <span className="h-8 w-8 rounded-full bg-green-500 flex items-center justify-center ring-8 ring-white">
                        <Activity className="h-4 w-4 text-white" />
                      </span>
                    </div>
                    <div className="flex-1 min-w-0">
                      <div>
                        <p className="text-sm text-gray-500">
                          Instance status changed to <StatusIndicator status={instance.status} size="sm" />
                        </p>
                        <p className="text-xs text-gray-400">
                          {instance.updated_at ? new Date(instance.updated_at).toLocaleString() : 'Recently'}
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              </li>
              <li>
                <div className="relative">
                  <div className="relative flex space-x-3">
                    <div>
                      <span className="h-8 w-8 rounded-full bg-blue-500 flex items-center justify-center ring-8 ring-white">
                        <Settings className="h-4 w-4 text-white" />
                      </span>
                    </div>
                    <div className="flex-1 min-w-0">
                      <div>
                        <p className="text-sm text-gray-500">Instance created</p>
                        <p className="text-xs text-gray-400">
                          {new Date(instance.created_at).toLocaleString()}
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  )
}

export default InstanceDetail
