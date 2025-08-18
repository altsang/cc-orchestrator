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

export interface WebSocketMessage {
  type: string
  data?: any
  timestamp?: string
}

// Log streaming types
export enum LogLevel {
  DEBUG = 'DEBUG',
  INFO = 'INFO',
  WARNING = 'WARNING',
  ERROR = 'ERROR',
  CRITICAL = 'CRITICAL',
}

export enum LogEntryType {
  SYSTEM = 'system',
  INSTANCE = 'instance',
  TASK = 'task',
  WORKTREE = 'worktree',
  WEB = 'web',
  CLI = 'cli',
  TMUX = 'tmux',
  INTEGRATION = 'integration',
  DATABASE = 'database',
  PROCESS = 'process',
}

export enum LogExportFormat {
  JSON = 'json',
  CSV = 'csv',
  TEXT = 'text',
}

export interface LogEntry {
  id: string;
  timestamp: string;
  level: LogLevel;
  logger: string;
  message: string;
  module?: string;
  function?: string;
  line?: number;
  context?: LogEntryType;
  instance_id?: string;
  task_id?: string;
  metadata: Record<string, any>;
  exception?: Record<string, any>;
}

export interface LogSearchRequest {
  query?: string;
  level?: LogLevel[];
  context?: LogEntryType[];
  instance_id?: string;
  task_id?: string;
  start_time?: string;
  end_time?: string;
  regex_enabled?: boolean;
  case_sensitive?: boolean;
  limit?: number;
  offset?: number;
}

export interface LogSearchResponse {
  entries: LogEntry[];
  total_count: number;
  has_more: boolean;
  search_duration_ms: number;
}

export interface LogExportRequest {
  search: LogSearchRequest;
  format: LogExportFormat;
  include_metadata?: boolean;
  filename?: string;
}

export interface LogStreamFilter {
  level?: LogLevel[];
  context?: LogEntryType[];
  instance_id?: string;
  task_id?: string;
  buffer_size?: number;
}

export interface LogStreamStats {
  active_streams: number;
  total_entries_streamed: number;
  stream_start_time: string;
  buffer_usage: Record<string, number>;
}

export interface InstanceUpdate {
  type: 'instance_update';
  data: Instance;
}

export interface TaskUpdate {
  type: 'task_update';
  data: Task;
}

export interface AlertMessage {
  type: 'alert';
  data: Alert;
}

export interface SystemStatusUpdate {
  type: 'system_status';
  data: {
    instances_count: number;
    running_instances: number;
    pending_tasks: number;
    active_tasks: number;
    system_health: HealthStatus;
    last_update: string;
  };
}

// Component props interfaces
export interface DashboardProps {
  className?: string;
}

export interface InstanceCardProps {
  instance: Instance;
  onStart?: (id: number) => void;
  onStop?: (id: number) => void;
  onViewDetails?: (id: number) => void;
}

export interface TaskCardProps {
  task: Task;
  onStart?: (id: number) => void;
  onComplete?: (id: number) => void;
  onCancel?: (id: number) => void;
  onAssign?: (id: number, instanceId: number) => void;
}

export interface StatusBadgeProps {
  status: InstanceStatus | TaskStatus | WorktreeStatus | HealthStatus;
  size?: 'sm' | 'md' | 'lg';
}

export interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

// Filter interfaces
export interface InstanceFilter {
  status?: InstanceStatus;
  health_status?: HealthStatus;
  branch_name?: string;
}

export interface TaskFilter {
  status?: TaskStatus;
  priority?: TaskPriority;
  instance_id?: number;
  worktree_id?: number;
}

export interface WorktreeFilter {
  status?: WorktreeStatus;
  branch_name?: string;
  instance_id?: number;
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
