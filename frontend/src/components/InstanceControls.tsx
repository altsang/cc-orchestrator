import React, { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Play, Square, RotateCcw, MoreVertical } from 'lucide-react'
import { apiClient } from '../services/api'
import { Instance, InstanceStatus } from '../types'

interface InstanceControlsProps {
  instance: Instance
}

const InstanceControls: React.FC<InstanceControlsProps> = ({ instance }) => {
  const [showMenu, setShowMenu] = useState(false)
  const queryClient = useQueryClient()

  const startMutation = useMutation({
    mutationFn: () => apiClient.startInstance(instance.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['instances'] })
    },
  })

  const stopMutation = useMutation({
    mutationFn: () => apiClient.stopInstance(instance.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['instances'] })
    },
  })

  const restartMutation = useMutation({
    mutationFn: () => apiClient.restartInstance(instance.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['instances'] })
    },
  })

  const canStart = instance.status === InstanceStatus.STOPPED || instance.status === InstanceStatus.ERROR
  const canStop = instance.status === InstanceStatus.RUNNING
  const canRestart = instance.status === InstanceStatus.RUNNING

  const handleAction = async (action: 'start' | 'stop' | 'restart') => {
    setShowMenu(false)

    try {
      switch (action) {
        case 'start':
          await startMutation.mutateAsync()
          break
        case 'stop':
          await stopMutation.mutateAsync()
          break
        case 'restart':
          await restartMutation.mutateAsync()
          break
      }
    } catch (error) {
      console.error(`Failed to ${action} instance:`, error)
    }
  }

  const isLoading = startMutation.isPending || stopMutation.isPending || restartMutation.isPending

  return (
    <div className="relative">
      <button
        type="button"
        className="rounded-md p-1 text-gray-400 hover:text-gray-500 focus:outline-none focus:ring-2 focus:ring-primary-500"
        onClick={() => setShowMenu(!showMenu)}
        disabled={isLoading}
      >
        {isLoading ? (
          <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-gray-900"></div>
        ) : (
          <MoreVertical className="h-5 w-5" />
        )}
      </button>

      {showMenu && (
        <div className="absolute right-0 z-10 mt-2 w-48 rounded-md bg-white py-1 shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none">
          {canStart && (
            <button
              className="flex w-full items-center px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 disabled:opacity-50"
              onClick={() => handleAction('start')}
              disabled={isLoading}
            >
              <Play className="mr-3 h-4 w-4 text-green-500" />
              Start Instance
            </button>
          )}

          {canStop && (
            <button
              className="flex w-full items-center px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 disabled:opacity-50"
              onClick={() => handleAction('stop')}
              disabled={isLoading}
            >
              <Square className="mr-3 h-4 w-4 text-red-500" />
              Stop Instance
            </button>
          )}

          {canRestart && (
            <button
              className="flex w-full items-center px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 disabled:opacity-50"
              onClick={() => handleAction('restart')}
              disabled={isLoading}
            >
              <RotateCcw className="mr-3 h-4 w-4 text-blue-500" />
              Restart Instance
            </button>
          )}
        </div>
      )}

      {/* Backdrop to close menu */}
      {showMenu && (
        <div
          className="fixed inset-0 z-0"
          onClick={() => setShowMenu(false)}
        />
      )}
    </div>
  )
}

export default InstanceControls
