import React from 'react'
import { AlertTriangle, CheckCircle, Clock, Square, AlertCircle } from 'lucide-react'
import { InstanceStatus } from '../types'

interface StatusIndicatorProps {
  status: InstanceStatus
  size?: 'sm' | 'md' | 'lg'
  showText?: boolean
  className?: string
}

const StatusIndicator: React.FC<StatusIndicatorProps> = ({
  status,
  size = 'md',
  showText = true,
  className = ''
}) => {
  const getStatusConfig = (status: InstanceStatus) => {
    switch (status) {
      case InstanceStatus.RUNNING:
        return {
          icon: CheckCircle,
          color: 'text-green-500',
          bgColor: 'bg-green-50',
          ringColor: 'ring-green-600/20',
          text: 'Running',
          animate: 'animate-pulse',
        }
      case InstanceStatus.STOPPED:
        return {
          icon: Square,
          color: 'text-gray-500',
          bgColor: 'bg-gray-50',
          ringColor: 'ring-gray-600/20',
          text: 'Stopped',
          animate: '',
        }
      case InstanceStatus.ERROR:
        return {
          icon: AlertTriangle,
          color: 'text-red-500',
          bgColor: 'bg-red-50',
          ringColor: 'ring-red-600/20',
          text: 'Error',
          animate: '',
        }
      case InstanceStatus.INITIALIZING:
        return {
          icon: Clock,
          color: 'text-yellow-500',
          bgColor: 'bg-yellow-50',
          ringColor: 'ring-yellow-600/20',
          text: 'Initializing',
          animate: 'animate-pulse-slow',
        }
      default:
        return {
          icon: AlertCircle,
          color: 'text-gray-400',
          bgColor: 'bg-gray-50',
          ringColor: 'ring-gray-600/20',
          text: 'Unknown',
          animate: '',
        }
    }
  }

  const getSizeConfig = (size: string) => {
    switch (size) {
      case 'sm':
        return {
          iconSize: 'h-3 w-3',
          textSize: 'text-xs',
          padding: 'px-1.5 py-0.5',
        }
      case 'lg':
        return {
          iconSize: 'h-6 w-6',
          textSize: 'text-base',
          padding: 'px-3 py-1.5',
        }
      default: // md
        return {
          iconSize: 'h-4 w-4',
          textSize: 'text-sm',
          padding: 'px-2 py-1',
        }
    }
  }

  const statusConfig = getStatusConfig(status)
  const sizeConfig = getSizeConfig(size)
  const Icon = statusConfig.icon

  if (!showText) {
    return (
      <div className={`inline-flex items-center ${className}`}>
        <Icon className={`${sizeConfig.iconSize} ${statusConfig.color} ${statusConfig.animate}`} />
      </div>
    )
  }

  return (
    <span
      className={`inline-flex items-center rounded-full ${sizeConfig.padding} ${sizeConfig.textSize} font-medium ring-1 ring-inset ${statusConfig.bgColor} ${statusConfig.color} ${statusConfig.ringColor} ${className}`}
    >
      <Icon className={`${sizeConfig.iconSize} mr-1 ${statusConfig.animate}`} />
      {statusConfig.text}
    </span>
  )
}

export default StatusIndicator
