import React, { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Activity, Server, AlertTriangle, Clock, TrendingUp } from 'lucide-react'
import InstanceGrid from '../components/InstanceGrid'
import ResourceChart from '../components/ResourceChart'
import StatusIndicator from '../components/StatusIndicator'
import { apiClient } from '../services/api'
import { InstanceStatus, InstanceMetrics } from '../types'
import { useWebSocket } from '../contexts/WebSocketContext'

const Dashboard: React.FC = () => {
  const [selectedMetricsInstance, setSelectedMetricsInstance] = useState<number | null>(null)
  const [metricsHistory, setMetricsHistory] = useState<InstanceMetrics[]>([])
  const { lastMessage, subscribe, isConnected } = useWebSocket()

  const { data: instancesData } = useQuery({
    queryKey: ['instances'],
    queryFn: () => apiClient.getInstances(),
    refetchInterval: 10000,
  })

  // Subscribe to metrics updates
  useEffect(() => {
    if (isConnected) {
      subscribe(['instance_metrics', 'system_events'])
    }
  }, [isConnected, subscribe])

  // Handle WebSocket metrics updates
  useEffect(() => {
    if (lastMessage?.type === 'instance_metrics') {
      const metrics = lastMessage.data as InstanceMetrics
      setMetricsHistory(prev => {
        const newHistory = [...prev, metrics].slice(-20) // Keep last 20 points
        return newHistory
      })
    }
  }, [lastMessage])

  const instances = instancesData?.instances || []

  // Calculate summary stats
  const stats = {
    total: instances.length,
    running: instances.filter(i => i.status === InstanceStatus.RUNNING).length,
    stopped: instances.filter(i => i.status === InstanceStatus.STOPPED).length,
    error: instances.filter(i => i.status === InstanceStatus.ERROR).length,
    initializing: instances.filter(i => i.status === InstanceStatus.INITIALIZING).length,
  }

  const statCards = [
    {
      name: 'Total Instances',
      value: stats.total,
      icon: Server,
      color: 'text-blue-600',
      bgColor: 'bg-blue-50',
    },
    {
      name: 'Running',
      value: stats.running,
      icon: Activity,
      color: 'text-green-600',
      bgColor: 'bg-green-50',
    },
    {
      name: 'Stopped',
      value: stats.stopped,
      icon: Clock,
      color: 'text-gray-600',
      bgColor: 'bg-gray-50',
    },
    {
      name: 'Error',
      value: stats.error,
      icon: AlertTriangle,
      color: 'text-red-600',
      bgColor: 'bg-red-50',
    },
  ]

  // Generate mock metrics for demonstration
  const generateMockMetrics = (instanceId: number): InstanceMetrics[] => {
    const now = new Date()
    return Array.from({ length: 10 }, (_, i) => ({
      instance_id: instanceId,
      cpu_usage: Math.random() * 80 + 10,
      memory_usage: Math.random() * 70 + 20,
      disk_usage: Math.random() * 50 + 30,
      network_in: Math.random() * 100,
      network_out: Math.random() * 100,
      uptime_seconds: 3600,
      timestamp: new Date(now.getTime() - (10 - i) * 60000).toISOString(),
    }))
  }

  const mockMetrics = selectedMetricsInstance
    ? generateMockMetrics(selectedMetricsInstance)
    : []

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="md:flex md:items-center md:justify-between">
        <div className="min-w-0 flex-1">
          <h2 className="text-2xl font-bold leading-7 text-gray-900 sm:truncate sm:text-3xl">
            Instance Dashboard
          </h2>
          <p className="mt-1 text-sm text-gray-500">
            Monitor and manage your Claude Code instances
          </p>
        </div>
        <div className="mt-4 flex md:ml-4 md:mt-0">
          <div className="flex items-center space-x-2">
            <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`} />
            <span className="text-sm text-gray-600">
              {isConnected ? 'Real-time updates active' : 'Offline mode'}
            </span>
          </div>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
        {statCards.map((stat) => (
          <div key={stat.name} className="card p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className={`p-3 rounded-md ${stat.bgColor}`}>
                  <stat.icon className={`h-6 w-6 ${stat.color}`} />
                </div>
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 truncate">
                    {stat.name}
                  </dt>
                  <dd className="flex items-baseline">
                    <div className="text-2xl font-semibold text-gray-900">
                      {stat.value}
                    </div>
                  </dd>
                </dl>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Resource Charts Section */}
      {instances.length > 0 && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-medium text-gray-900">Resource Usage</h3>
            <select
              className="rounded-md border border-gray-300 bg-white py-2 pl-3 pr-10 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
              value={selectedMetricsInstance || ''}
              onChange={(e) => setSelectedMetricsInstance(e.target.value ? Number(e.target.value) : null)}
            >
              <option value="">Select Instance</option>
              {instances.map((instance) => (
                <option key={instance.id} value={instance.id}>
                  Issue #{instance.issue_id} - {instance.status}
                </option>
              ))}
            </select>
          </div>

          {selectedMetricsInstance && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <ResourceChart
                metrics={mockMetrics}
                type="cpu"
                title="CPU Usage"
                color="#3b82f6"
              />
              <ResourceChart
                metrics={mockMetrics}
                type="memory"
                title="Memory Usage"
                color="#22c55e"
              />
              <ResourceChart
                metrics={mockMetrics}
                type="disk"
                title="Disk Usage"
                color="#f59e0b"
              />
            </div>
          )}
        </div>
      )}

      {/* Instance Grid */}
      <div className="space-y-4">
        <h3 className="text-lg font-medium text-gray-900">Instances</h3>
        <InstanceGrid />
      </div>
    </div>
  )
}

export default Dashboard
