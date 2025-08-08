// Type definitions for CC-Orchestrator API

export enum InstanceStatus {
  INITIALIZING = 'initializing',
  RUNNING = 'running',
  STOPPED = 'stopped',
  FAILED = 'failed',
  TERMINATING = 'terminating',
}

export enum HealthStatus {
  HEALTHY = 'healthy',
  DEGRADED = 'degraded',
  UNHEALTHY = 'unhealthy',
  UNKNOWN = 'unknown',
}

export enum TaskStatus {
  PENDING = 'pending',
  RUNNING = 'running',
  IN_PROGRESS = 'in_progress',
  COMPLETED = 'completed',
  FAILED = 'failed',
  CANCELLED = 'cancelled',
}

export enum TaskPriority {
  LOW = 'low',
  MEDIUM = 'medium',
  HIGH = 'high',
  CRITICAL = 'critical',
}

export enum WorktreeStatus {
  ACTIVE = 'active',
  INACTIVE = 'inactive',
  CLEANUP = 'cleanup',
  ERROR = 'error',
}

export enum AlertLevel {
  INFO = 'info',
  WARNING = 'warning',
  ERROR = 'error',
  CRITICAL = 'critical',
}

// Alias for backward compatibility with tests
export enum AlertSeverity {
  LOW = 'low',
  MEDIUM = 'medium',
  HIGH = 'high',
  CRITICAL = 'critical',
}

export interface Instance {
  id: number;
  issue_id: string;
  status: InstanceStatus;
  workspace_path?: string;
  branch_name?: string;
  tmux_session?: string;
  process_id?: number;
  health_status: HealthStatus;
  extra_metadata: Record<string, any>;
  created_at: string;
  updated_at: string;
  last_health_check?: string;
  health_check_count: number;
  healthy_check_count: number;
  last_recovery_attempt?: string;
  recovery_attempt_count: number;
  health_check_details?: string;
  last_activity?: string;
}

export interface Task {
  id: number;
  title: string;
  description?: string;
  status: TaskStatus;
  priority: TaskPriority;
  instance_id?: number;
  worktree_id?: number;
  due_date?: string;
  estimated_duration?: number;
  requirements: Record<string, any>;
  extra_metadata: Record<string, any>;
  created_at: string;
  updated_at: string;
  started_at?: string;
  completed_at?: string;
  actual_duration?: number;
  results: Record<string, any>;
}

export interface Worktree {
  id: number;
  name: string;
  path: string;
  branch_name: string;
  repository_url?: string;
  status: WorktreeStatus;
  instance_id?: number;
  current_commit?: string;
  has_uncommitted_changes: boolean;
  git_config: Record<string, any>;
  extra_metadata: Record<string, any>;
  created_at: string;
  updated_at: string;
  last_sync?: string;
}

export interface Alert {
  id: number;
  instance_id?: number;
  alert_id: string;
  title?: string;
  level?: AlertLevel;
  severity?: AlertSeverity | string;
  status?: string;
  message: string;
  details?: string;
  timestamp?: string;
  metadata?: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface HealthCheck {
  id: number;
  instance_id: number;
  overall_status: HealthStatus;
  check_results: string;
  duration_ms: number;
  check_timestamp: string;
  created_at: string;
  updated_at: string;
}

export interface Configuration {
  id: number;
  key: string;
  value: string;
  scope: string;
  instance_id?: number;
  description?: string;
  is_secret: boolean;
  is_readonly: boolean;
  extra_metadata: Record<string, any>;
  created_at: string;
  updated_at: string;
}

// API Response types
export interface APIResponse<T = any> {
  success: boolean;
  message: string;
  data?: T;
}

export interface PaginatedResponse<T = any> {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export interface ErrorResponse {
  success: false;
  error: string;
  message: string;
  details?: Record<string, any>;
}

// WebSocket message types
export interface WebSocketMessage {
  type: string;
  topic?: string;
  data: any;
  timestamp: string;
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
