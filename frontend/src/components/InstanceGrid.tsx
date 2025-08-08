import React, { useEffect } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Play, Square, RotateCcw, AlertTriangle, Clock, CheckCircle } from 'lucide-react'
import { apiClient } from '../services/api'
import { Instance, InstanceStatus } from '../types'
import { useWebSocket } from '../contexts/WebSocketContext'
import InstanceControls from './InstanceControls'

const InstanceGrid: React.FC = () => {
  const queryClient = useQueryClient()
  const { lastMessage, subscribe, isConnected } = useWebSocket()

  const { data, isLoading, error } = useQuery({
    queryKey: ['instances'],
    queryFn: () => apiClient.getInstances(),
    refetchInterval: 10000, // Refetch every 10 seconds
  })

  // Subscribe to real-time updates
  useEffect(() => {
    if (isConnected) {
      subscribe(['instance_status', 'instance_metrics'])
    }
  }, [isConnected, subscribe])

  // Handle WebSocket messages
  useEffect(() => {
    if (lastMessage?.type === 'instance_status_change') {
      queryClient.invalidateQueries({ queryKey: ['instances'] })
    }
  }, [lastMessage, queryClient])

  const getStatusIcon = (status: InstanceStatus) => {
    switch (status) {
      case InstanceStatus.RUNNING:
        return <CheckCircle className="h-5 w-5 text-green-500" />
      case InstanceStatus.STOPPED:
        return <Square className="h-5 w-5 text-gray-500" />
      case InstanceStatus.FAILED:
        return <AlertTriangle className="h-5 w-5 text-red-500" />
      case InstanceStatus.PENDING:
        return <Clock className="h-5 w-5 text-yellow-500" />
      default:
        return <AlertTriangle className="h-5 w-5 text-gray-400" />
    }
  }

  const getStatusColor = (status: InstanceStatus) => {
    switch (status) {
      case InstanceStatus.RUNNING:
        return 'bg-green-50 text-green-700 ring-green-600/20'
      case InstanceStatus.STOPPED:
        return 'bg-gray-50 text-gray-700 ring-gray-600/20'
      case InstanceStatus.FAILED:
        return 'bg-red-50 text-red-700 ring-red-600/20'
      case InstanceStatus.PENDING:
        return 'bg-yellow-50 text-yellow-700 ring-yellow-600/20'
      default:
        return 'bg-gray-50 text-gray-700 ring-gray-600/20'
    }
  }

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {[...Array(6)].map((_, i) => (
          <div key={i} className="card p-6 animate-pulse">
            <div className="h-4 bg-gray-200 rounded w-1/2 mb-4"></div>
            <div className="h-3 bg-gray-200 rounded w-1/4 mb-2"></div>
            <div className="h-3 bg-gray-200 rounded w-1/3"></div>
          </div>
        ))}
      </div>
    )
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <AlertTriangle className="mx-auto h-12 w-12 text-red-400" />
        <h3 className="mt-2 text-sm font-medium text-gray-900">Error loading instances</h3>
        <p className="mt-1 text-sm text-gray-500">
          {error instanceof Error ? error.message : 'Something went wrong'}
        </p>
      </div>
    )
  }

  if (!data?.instances.length) {
    return (
      <div className="text-center py-12">
        <div className="mx-auto h-12 w-12 text-gray-400">
          <svg fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z"
            />
          </svg>
        </div>
        <h3 className="mt-2 text-sm font-medium text-gray-900">No instances</h3>
        <p className="mt-1 text-sm text-gray-500">
          Get started by creating a new instance.
        </p>
      </div>
    )
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      {data.instances.map((instance: Instance) => (
        <div key={instance.id} className="card p-6 hover:shadow-md transition-shadow">
          <div className="flex items-start justify-between">
            <div className="flex items-center">
              {getStatusIcon(instance.status)}
              <div className="ml-3">
                <h3 className="text-lg font-medium text-gray-900">
                  Issue #{instance.issue_id}
                </h3>
                <div className="mt-1 flex items-center">
                  <span
                    className={`inline-flex items-center rounded-full px-2 py-1 text-xs font-medium ring-1 ring-inset ${getStatusColor(
                      instance.status
                    )}`}
                  >
                    {instance.status}
                  </span>
                </div>
              </div>
            </div>

            <InstanceControls instance={instance} />
          </div>

          <div className="mt-4">
            <dl className="grid grid-cols-1 gap-x-4 gap-y-2 sm:grid-cols-2">
              <div>
                <dt className="text-sm font-medium text-gray-500">Created</dt>
                <dd className="mt-1 text-sm text-gray-900">
                  {new Date(instance.created_at).toLocaleDateString()}
                </dd>
              </div>
              {instance.updated_at && (
                <div>
                  <dt className="text-sm font-medium text-gray-500">Updated</dt>
                  <dd className="mt-1 text-sm text-gray-900">
                    {new Date(instance.updated_at).toLocaleString()}
                  </dd>
                </div>
              )}
            </dl>
          </div>

          <div className="mt-4">
            <button
              type="button"
              className="text-sm font-medium text-primary-600 hover:text-primary-500"
              onClick={() => {
                // TODO: Navigate to instance detail page
                console.log('Navigate to instance:', instance.id)
              }}
            >
              View details →
            </button>
          </div>
        </div>
      ))}
    </div>
  )
}

export default InstanceGrid
