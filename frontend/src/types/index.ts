export interface Instance {
  id: number
  issue_id: string
  status: InstanceStatus
  created_at: string
  updated_at: string | null
}

export enum InstanceStatus {
  INITIALIZING = 'INITIALIZING',
  RUNNING = 'RUNNING',
  STOPPED = 'STOPPED',
  ERROR = 'ERROR'
}

export interface InstanceMetrics {
  instance_id: number
  cpu_usage: number
  memory_usage: number
  disk_usage: number
  network_in: number
  network_out: number
  uptime_seconds: number
  timestamp: string
}

export interface InstanceHealth {
  instance_id: number
  status: InstanceStatus
  health: string
  cpu_usage: number
  memory_usage: number
  uptime_seconds: number
  last_activity: string | null
}

export interface LogEntry {
  id: string
  timestamp: string
  level: 'DEBUG' | 'INFO' | 'WARNING' | 'ERROR' | 'CRITICAL'
  message: string
  context?: Record<string, any>
}

export interface WebSocketMessage {
  type: string
  data?: any
  timestamp?: string
}

export interface SystemStatus {
  total_instances: number
  running_instances: number
  stopped_instances: number
  failed_instances: number
  pending_instances: number
  system_cpu_usage: number
  system_memory_usage: number
  active_connections: number
}
