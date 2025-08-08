// Tests for type definitions to ensure coverage

import * as Types from '../index';

describe('Type definitions', () => {
  describe('Enums', () => {
    it('should export InstanceStatus enum', () => {
      expect(Types.InstanceStatus.INITIALIZING).toBe('initializing');
      expect(Types.InstanceStatus.RUNNING).toBe('running');
      expect(Types.InstanceStatus.STOPPED).toBe('stopped');
      expect(Types.InstanceStatus.FAILED).toBe('failed');
      expect(Types.InstanceStatus.TERMINATING).toBe('terminating');
    });

    it('should export HealthStatus enum', () => {
      expect(Types.HealthStatus.HEALTHY).toBe('healthy');
      expect(Types.HealthStatus.DEGRADED).toBe('degraded');
      expect(Types.HealthStatus.UNHEALTHY).toBe('unhealthy');
      expect(Types.HealthStatus.UNKNOWN).toBe('unknown');
    });

    it('should export TaskStatus enum', () => {
      expect(Types.TaskStatus.PENDING).toBe('pending');
      expect(Types.TaskStatus.RUNNING).toBe('running');
      expect(Types.TaskStatus.IN_PROGRESS).toBe('in_progress');
      expect(Types.TaskStatus.COMPLETED).toBe('completed');
      expect(Types.TaskStatus.FAILED).toBe('failed');
      expect(Types.TaskStatus.CANCELLED).toBe('cancelled');
    });

    it('should export TaskPriority enum', () => {
      expect(Types.TaskPriority.LOW).toBe('low');
      expect(Types.TaskPriority.MEDIUM).toBe('medium');
      expect(Types.TaskPriority.HIGH).toBe('high');
      expect(Types.TaskPriority.CRITICAL).toBe('critical');
    });

    it('should export WorktreeStatus enum', () => {
      expect(Types.WorktreeStatus.ACTIVE).toBe('active');
      expect(Types.WorktreeStatus.INACTIVE).toBe('inactive');
      expect(Types.WorktreeStatus.CLEANUP).toBe('cleanup');
      expect(Types.WorktreeStatus.ERROR).toBe('error');
    });

    it('should export AlertLevel enum', () => {
      expect(Types.AlertLevel.INFO).toBe('info');
      expect(Types.AlertLevel.WARNING).toBe('warning');
      expect(Types.AlertLevel.ERROR).toBe('error');
      expect(Types.AlertLevel.CRITICAL).toBe('critical');
    });

    it('should export AlertSeverity enum for backward compatibility', () => {
      expect(Types.AlertSeverity.LOW).toBe('low');
      expect(Types.AlertSeverity.MEDIUM).toBe('medium');
      expect(Types.AlertSeverity.HIGH).toBe('high');
      expect(Types.AlertSeverity.CRITICAL).toBe('critical');
    });
  });

  describe('Type validation', () => {
    it('should validate Instance interface structure', () => {
      const instance: Types.Instance = {
        id: 1,
        issue_id: 'ISSUE-123',
        status: Types.InstanceStatus.RUNNING,
        health_status: Types.HealthStatus.HEALTHY,
        extra_metadata: {},
        created_at: '2023-01-01T00:00:00Z',
        updated_at: '2023-01-01T01:00:00Z',
        health_check_count: 5,
        healthy_check_count: 4,
        recovery_attempt_count: 0,
      };

      expect(instance.id).toBe(1);
      expect(instance.issue_id).toBe('ISSUE-123');
      expect(instance.status).toBe(Types.InstanceStatus.RUNNING);
      expect(instance.health_status).toBe(Types.HealthStatus.HEALTHY);
    });

    it('should validate Task interface structure', () => {
      const task: Types.Task = {
        id: 1,
        title: 'Test Task',
        status: Types.TaskStatus.PENDING,
        priority: Types.TaskPriority.HIGH,
        requirements: {},
        extra_metadata: {},
        created_at: '2023-01-01T00:00:00Z',
        updated_at: '2023-01-01T01:00:00Z',
        results: {},
      };

      expect(task.id).toBe(1);
      expect(task.title).toBe('Test Task');
      expect(task.status).toBe(Types.TaskStatus.PENDING);
      expect(task.priority).toBe(Types.TaskPriority.HIGH);
    });

    it('should validate Alert interface structure', () => {
      const alert: Types.Alert = {
        id: 1,
        alert_id: 'ALERT-123',
        message: 'Test alert',
        created_at: '2023-01-01T00:00:00Z',
        updated_at: '2023-01-01T01:00:00Z',
      };

      expect(alert.id).toBe(1);
      expect(alert.alert_id).toBe('ALERT-123');
      expect(alert.message).toBe('Test alert');
    });

    it('should validate PaginatedResponse interface structure', () => {
      const response: Types.PaginatedResponse<Types.Instance> = {
        items: [],
        total: 0,
        page: 1,
        size: 20,
        pages: 1,
      };

      expect(response.items).toEqual([]);
      expect(response.total).toBe(0);
      expect(response.page).toBe(1);
      expect(response.size).toBe(20);
      expect(response.pages).toBe(1);
    });

    it('should validate APIResponse interface structure', () => {
      const response: Types.APIResponse<string> = {
        success: true,
        message: 'Success',
        data: 'test data',
      };

      expect(response.success).toBe(true);
      expect(response.message).toBe('Success');
      expect(response.data).toBe('test data');
    });

    it('should validate WebSocketMessage interface structure', () => {
      const message: Types.WebSocketMessage = {
        type: 'test',
        data: { value: 123 },
        timestamp: '2023-01-01T00:00:00Z',
      };

      expect(message.type).toBe('test');
      expect(message.data.value).toBe(123);
      expect(message.timestamp).toBe('2023-01-01T00:00:00Z');
    });

    it('should validate filter interfaces', () => {
      const instanceFilter: Types.InstanceFilter = {
        status: Types.InstanceStatus.RUNNING,
        health_status: Types.HealthStatus.HEALTHY,
        branch_name: 'main',
      };

      const taskFilter: Types.TaskFilter = {
        status: Types.TaskStatus.PENDING,
        priority: Types.TaskPriority.HIGH,
        instance_id: 1,
      };

      expect(instanceFilter.status).toBe(Types.InstanceStatus.RUNNING);
      expect(taskFilter.status).toBe(Types.TaskStatus.PENDING);
    });
  });
});
