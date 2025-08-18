import React, { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Search, Filter, Download, RefreshCw } from 'lucide-react'
import { apiClient } from '../services/api'
import { LogEntry, InstanceStatus } from '../types'
import StatusIndicator from '../components/StatusIndicator'

const Logs: React.FC = () => {
  const [selectedInstance, setSelectedInstance] = useState<number | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [logLevel, setLogLevel] = useState<string>('')
  const [autoRefresh, setAutoRefresh] = useState(false)

  const { data: instancesData } = useQuery({
    queryKey: ['instances'],
    queryFn: () => apiClient.getInstances(),
  })

  const { data: logsData, refetch, isLoading } = useQuery({
    queryKey: ['logs', selectedInstance, searchQuery],
    queryFn: () =>
      selectedInstance
        ? apiClient.getInstanceLogs(selectedInstance, {
            limit: 100,
            search: searchQuery || undefined
          })
        : Promise.resolve({ instance_id: 0, logs: [], total: 0, limit: 100 }),
    enabled: !!selectedInstance,
    refetchInterval: autoRefresh ? 5000 : false,
  })

  // Generate mock log entries for demonstration
  const generateMockLogs = (instanceId: number): LogEntry[] => {
    const levels: LogEntry['level'][] = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
    const messages = [
      'Claude instance initialized successfully',
      'Processing task assignment',
      'WebSocket connection established',
      'Health check completed',
      'Resource usage within normal limits',
      'Task execution started',
      'API request processed',
      'Configuration updated',
      'Session cleanup initiated',
      'Memory usage warning threshold reached',
      'Network connectivity restored',
      'Process spawned successfully'
    ]

    return Array.from({ length: 50 }, (_, i) => ({
      id: `log-${instanceId}-${i}`,
      timestamp: new Date(Date.now() - i * 60000).toISOString(),
      level: levels[Math.floor(Math.random() * levels.length)],
      message: messages[Math.floor(Math.random() * messages.length)],
      context: {
        instance_id: instanceId,
        process_id: Math.floor(Math.random() * 10000),
        memory_mb: Math.floor(Math.random() * 512),
      }
    }))
  }

  const mockLogs = selectedInstance ? generateMockLogs(selectedInstance) : []

  // Filter logs by level if specified
  const filteredLogs = mockLogs.filter(log =>
    !logLevel || log.level === logLevel
  )

  const getLevelColor = (level: LogEntry['level']) => {
    switch (level) {
      case 'DEBUG':
        return 'text-gray-600 bg-gray-50'
      case 'INFO':
        return 'text-blue-600 bg-blue-50'
      case 'WARNING':
        return 'text-yellow-600 bg-yellow-50'
      case 'ERROR':
        return 'text-red-600 bg-red-50'
      case 'CRITICAL':
        return 'text-red-700 bg-red-100'
      default:
        return 'text-gray-600 bg-gray-50'
    }
  }

  const instances = instancesData?.instances || []

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="md:flex md:items-center md:justify-between">
        <div className="min-w-0 flex-1">
          <h2 className="text-2xl font-bold leading-7 text-gray-900 sm:truncate sm:text-3xl">
            Instance Logs
          </h2>
          <p className="mt-1 text-sm text-gray-500">
            View and search instance logs in real-time
          </p>
        </div>
        <div className="mt-4 flex space-x-3 md:ml-4 md:mt-0">
          <button
            type="button"
            className={`inline-flex items-center rounded-md px-3 py-2 text-sm font-semibold shadow-sm ring-1 ring-inset ${
              autoRefresh
                ? 'bg-primary-600 text-white ring-primary-600 hover:bg-primary-500'
                : 'bg-white text-gray-900 ring-gray-300 hover:bg-gray-50'
            }`}
            onClick={() => setAutoRefresh(!autoRefresh)}
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${autoRefresh ? 'animate-spin' : ''}`} />
            Auto Refresh
          </button>
          <button
            type="button"
            className="inline-flex items-center rounded-md bg-white px-3 py-2 text-sm font-semibold text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 hover:bg-gray-50"
            onClick={() => refetch()}
          >
            <Download className="h-4 w-4 mr-2" />
            Export
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white shadow rounded-lg">
        <div className="p-4 border-b border-gray-200">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Instance Selector */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Instance
              </label>
              <select
                className="w-full rounded-md border border-gray-300 bg-white py-2 pl-3 pr-10 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                value={selectedInstance || ''}
                onChange={(e) => setSelectedInstance(e.target.value ? Number(e.target.value) : null)}
              >
                <option value="">Select Instance</option>
                {instances.map((instance) => (
                  <option key={instance.id} value={instance.id}>
                    Issue #{instance.issue_id}
                  </option>
                ))}
              </select>
            </div>

            {/* Search */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Search
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Search className="h-5 w-5 text-gray-400" />
                </div>
                <input
                  type="text"
                  className="w-full pl-10 pr-3 py-2 border border-gray-300 rounded-md text-sm placeholder-gray-500 focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                  placeholder="Search logs..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
              </div>
            </div>

            {/* Log Level Filter */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Log Level
              </label>
              <select
                className="w-full rounded-md border border-gray-300 bg-white py-2 pl-3 pr-10 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                value={logLevel}
                onChange={(e) => setLogLevel(e.target.value)}
              >
                <option value="">All Levels</option>
                <option value="DEBUG">Debug</option>
                <option value="INFO">Info</option>
                <option value="WARNING">Warning</option>
                <option value="ERROR">Error</option>
                <option value="CRITICAL">Critical</option>
              </select>
            </div>
          </div>
        </div>

        {/* Logs Display */}
        <div className="max-h-96 overflow-y-auto">
          {!selectedInstance ? (
            <div className="text-center py-12">
              <Filter className="mx-auto h-12 w-12 text-gray-400" />
              <h3 className="mt-2 text-sm font-medium text-gray-900">No instance selected</h3>
              <p className="mt-1 text-sm text-gray-500">
                Select an instance to view its logs.
              </p>
            </div>
          ) : isLoading ? (
            <div className="text-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900 mx-auto"></div>
              <p className="mt-2 text-sm text-gray-500">Loading logs...</p>
            </div>
          ) : filteredLogs.length === 0 ? (
            <div className="text-center py-12">
              <div className="mx-auto h-12 w-12 text-gray-400">
                <svg fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>
              <h3 className="mt-2 text-sm font-medium text-gray-900">No logs found</h3>
              <p className="mt-1 text-sm text-gray-500">
                No logs match your current filters.
              </p>
            </div>
          ) : (
            <div className="divide-y divide-gray-200">
              {filteredLogs.map((log) => (
                <div key={log.id} className="p-4 hover:bg-gray-50">
                  <div className="flex items-start space-x-3">
                    <div className="flex-shrink-0">
                      <span className={`inline-flex items-center rounded px-2 py-1 text-xs font-medium ${getLevelColor(log.level)}`}>
                        {log.level}
                      </span>
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between">
                        <p className="text-sm text-gray-900 break-words">
                          {log.message}
                        </p>
                        <p className="text-xs text-gray-500 flex-shrink-0 ml-4">
                          {new Date(log.timestamp).toLocaleString()}
                        </p>
                      </div>
                      {log.context && (
                        <div className="mt-2 text-xs text-gray-500 bg-gray-50 p-2 rounded">
                          <pre className="whitespace-pre-wrap">
                            {JSON.stringify(log.context, null, 2)}
                          </pre>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default Logs
