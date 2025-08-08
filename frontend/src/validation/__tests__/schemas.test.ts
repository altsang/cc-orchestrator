import { z } from 'zod';
import logger from '../../utils/logger';
import {
  sanitizeString,
  sanitizeObject,
  validateApiResponse,
  safeParseWebSocketMessage,
  instanceSchema,
  taskSchema,
  worktreeSchema,
  alertSchema,
  healthStatusSchema,
  paginatedResponseSchema,
  webSocketMessageSchema,
  instanceStatusSchema,
  taskStatusSchema,
  alertSeveritySchema,
} from '../schemas';
import { InstanceStatus, TaskStatus, AlertSeverity } from '../../types';

// Mock logger
jest.mock('../../utils/logger', () => ({
  error: jest.fn(),
}));

const mockLogger = logger as jest.Mocked<typeof logger>;

describe('Validation Schemas', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('sanitization functions', () => {
    describe('sanitizeString', () => {
      it('should trim whitespace', () => {
        expect(sanitizeString('  hello world  ')).toBe('hello world');
      });

      it('should remove HTML tags', () => {
        expect(sanitizeString('hello <script>alert("xss")</script> world')).toBe('hello alert("xss") world');
        expect(sanitizeString('<div>content</div>')).toBe('content');
        expect(sanitizeString('text with <> symbols')).toBe('text with  symbols');
      });

      it('should limit string length', () => {
        const longString = 'a'.repeat(2000);
        const result = sanitizeString(longString);
        expect(result).toHaveLength(1000);
        expect(result).toBe('a'.repeat(1000));
      });

      it('should handle empty strings', () => {
        expect(sanitizeString('')).toBe('');
      });

      it('should handle strings with only whitespace', () => {
        expect(sanitizeString('   \n\t   ')).toBe('');
      });

      it('should preserve valid content', () => {
        expect(sanitizeString('Hello World 123')).toBe('Hello World 123');
      });
    });

    describe('sanitizeObject', () => {
      it('should sanitize string values in object', () => {
        const input = {
          name: '  John Doe  ',
          description: 'Hello <script>alert("xss")</script>',
          number: 123,
          boolean: true,
        };

        const result = sanitizeObject(input);

        expect(result).toEqual({
          name: 'John Doe',
          description: 'Hello alert("xss")',
          number: 123,
          boolean: true,
        });
      });

      it('should handle nested objects', () => {
        const input = {
          user: {
            name: '  Alice  ',
            bio: '<div>Developer</div>',
          },
          tags: ['<script>tag1</script>', '  tag2  '],
        };

        const result = sanitizeObject(input);

        expect(result.user.name).toBe('Alice');
        expect(result.user.bio).toBe('Developer');
        expect(result.tags).toEqual(['tag1', 'tag2']);
      });

      it('should handle null and undefined values', () => {
        const input = {
          name: '  Test  ',
          nullable: null,
          undefined: undefined,
        };

        const result = sanitizeObject(input);

        expect(result).toEqual({
          name: 'Test',
          nullable: null,
          undefined: undefined,
        });
      });

      it('should handle arrays', () => {
        const input = {
          items: ['  item1  ', '<script>item2</script>', 123, null],
        };

        const result = sanitizeObject(input);

        expect(result.items).toEqual(['item1', 'item2', 123, null]);
      });
    });
  });

  describe('enum schemas', () => {
    describe('instanceStatusSchema', () => {
      it('should validate valid instance statuses', () => {
        expect(instanceStatusSchema.parse('initializing')).toBe('initializing');
        expect(instanceStatusSchema.parse('running')).toBe('running');
        expect(instanceStatusSchema.parse('stopped')).toBe('stopped');
        expect(instanceStatusSchema.parse('failed')).toBe('failed');
        expect(instanceStatusSchema.parse('terminating')).toBe('terminating');
      });

      it('should reject invalid instance statuses', () => {
        expect(() => instanceStatusSchema.parse('invalid')).toThrow();
        expect(() => instanceStatusSchema.parse('')).toThrow();
        expect(() => instanceStatusSchema.parse(null)).toThrow();
      });
    });

    describe('taskStatusSchema', () => {
      it('should validate valid task statuses', () => {
        expect(taskStatusSchema.parse('pending')).toBe('pending');
        expect(taskStatusSchema.parse('running')).toBe('running');
        expect(taskStatusSchema.parse('completed')).toBe('completed');
        expect(taskStatusSchema.parse('failed')).toBe('failed');
        expect(taskStatusSchema.parse('cancelled')).toBe('cancelled');
      });

      it('should reject invalid task statuses', () => {
        expect(() => taskStatusSchema.parse('invalid')).toThrow();
      });
    });

    describe('alertSeveritySchema', () => {
      it('should validate valid alert severities', () => {
        expect(alertSeveritySchema.parse('low')).toBe('low');
        expect(alertSeveritySchema.parse('medium')).toBe('medium');
        expect(alertSeveritySchema.parse('high')).toBe('high');
        expect(alertSeveritySchema.parse('critical')).toBe('critical');
      });

      it('should reject invalid alert severities', () => {
        expect(() => alertSeveritySchema.parse('invalid')).toThrow();
      });
    });
  });

  describe('entity schemas', () => {
    describe('instanceSchema', () => {
      const validInstance = {
        id: 1,
        instance_id: 'inst-123',
        issue_id: 'ISSUE-456',
        status: 'running',
        branch: 'main',
        workspace_path: '/workspace/path',
        created_at: '2023-01-01T00:00:00Z',
        updated_at: '2023-01-01T01:00:00Z',
        metadata: {},
      };

      it('should validate valid instance', () => {
        const result = instanceSchema.parse(validInstance);
        expect(result).toEqual(validInstance);
      });

      it('should require all mandatory fields', () => {
        const { id, ...withoutId } = validInstance;
        expect(() => instanceSchema.parse(withoutId)).toThrow();

        const { instance_id, ...withoutInstanceId } = validInstance;
        expect(() => instanceSchema.parse(withoutInstanceId)).toThrow();

        const { status, ...withoutStatus } = validInstance;
        expect(() => instanceSchema.parse(withoutStatus)).toThrow();
      });

      it('should validate field types', () => {
        expect(() => instanceSchema.parse({ ...validInstance, id: 'not-a-number' })).toThrow();
        expect(() => instanceSchema.parse({ ...validInstance, status: 'invalid-status' })).toThrow();
        expect(() => instanceSchema.parse({ ...validInstance, created_at: 'invalid-date' })).toThrow();
      });

      it('should accept optional fields as null', () => {
        const instanceWithNulls = {
          ...validInstance,
          branch: null,
          workspace_path: null,
          metadata: null,
        };
        
        expect(() => instanceSchema.parse(instanceWithNulls)).not.toThrow();
      });
    });

    describe('taskSchema', () => {
      const validTask = {
        id: 1,
        task_id: 'task-123',
        title: 'Test Task',
        description: 'Task description',
        status: 'pending',
        priority: 'high',
        assigned_instance_id: null,
        created_at: '2023-01-01T00:00:00Z',
        updated_at: '2023-01-01T01:00:00Z',
        due_date: null,
        metadata: {},
      };

      it('should validate valid task', () => {
        const result = taskSchema.parse(validTask);
        expect(result).toEqual(validTask);
      });

      it('should require mandatory fields', () => {
        const { title, ...withoutTitle } = validTask;
        expect(() => taskSchema.parse(withoutTitle)).toThrow();

        const { status, ...withoutStatus } = validTask;
        expect(() => taskSchema.parse(withoutStatus)).toThrow();
      });

      it('should validate optional fields', () => {
        const taskWithOptionals = {
          ...validTask,
          assigned_instance_id: 'inst-123',
          due_date: '2023-12-31T23:59:59Z',
        };
        
        expect(() => taskSchema.parse(taskWithOptionals)).not.toThrow();
      });
    });

    describe('worktreeSchema', () => {
      const validWorktree = {
        id: 1,
        worktree_id: 'wt-123',
        path: '/worktree/path',
        branch: 'feature-branch',
        instance_id: 1,
        created_at: '2023-01-01T00:00:00Z',
        updated_at: '2023-01-01T01:00:00Z',
        metadata: {},
      };

      it('should validate valid worktree', () => {
        const result = worktreeSchema.parse(validWorktree);
        expect(result).toEqual(validWorktree);
      });

      it('should require mandatory fields', () => {
        const { path, ...withoutPath } = validWorktree;
        expect(() => worktreeSchema.parse(withoutPath)).toThrow();

        const { branch, ...withoutBranch } = validWorktree;
        expect(() => worktreeSchema.parse(withoutBranch)).toThrow();
      });
    });

    describe('alertSchema', () => {
      const validAlert = {
        id: 1,
        alert_id: 'alert-123',
        title: 'Test Alert',
        message: 'Alert message',
        severity: 'high',
        status: 'active',
        created_at: '2023-01-01T00:00:00Z',
        updated_at: '2023-01-01T01:00:00Z',
        metadata: {},
      };

      it('should validate valid alert', () => {
        const result = alertSchema.parse(validAlert);
        expect(result).toEqual(validAlert);
      });

      it('should require mandatory fields', () => {
        const { title, ...withoutTitle } = validAlert;
        expect(() => alertSchema.parse(withoutTitle)).toThrow();

        const { severity, ...withoutSeverity } = validAlert;
        expect(() => alertSchema.parse(withoutSeverity)).toThrow();
      });

      it('should validate severity values', () => {
        expect(() => alertSchema.parse({ ...validAlert, severity: 'invalid' })).toThrow();
      });
    });

    describe('healthStatusSchema', () => {
      const validHealthStatus = {
        id: 1,
        component: 'database',
        status: 'healthy',
        message: 'All systems operational',
        checked_at: '2023-01-01T00:00:00Z',
        metadata: {},
      };

      it('should validate valid health status', () => {
        const result = healthStatusSchema.parse(validHealthStatus);
        expect(result).toEqual(validHealthStatus);
      });

      it('should require mandatory fields', () => {
        const { component, ...withoutComponent } = validHealthStatus;
        expect(() => healthStatusSchema.parse(withoutComponent)).toThrow();

        const { status, ...withoutStatus } = validHealthStatus;
        expect(() => healthStatusSchema.parse(withoutStatus)).toThrow();
      });
    });
  });

  describe('paginatedResponseSchema', () => {
    const validPaginatedResponse = {
      items: [{ id: 1, name: 'test' }],
      total: 1,
      page: 1,
      size: 20,
      pages: 1,
    };

    it('should validate valid paginated response', () => {
      const result = paginatedResponseSchema.parse(validPaginatedResponse);
      expect(result).toEqual(validPaginatedResponse);
    });

    it('should require all pagination fields', () => {
      const { total, ...withoutTotal } = validPaginatedResponse;
      expect(() => paginatedResponseSchema.parse(withoutTotal)).toThrow();

      const { page, ...withoutPage } = validPaginatedResponse;
      expect(() => paginatedResponseSchema.parse(withoutPage)).toThrow();

      const { size, ...withoutSize } = validPaginatedResponse;
      expect(() => paginatedResponseSchema.parse(withoutSize)).toThrow();

      const { pages, ...withoutPages } = validPaginatedResponse;
      expect(() => paginatedResponseSchema.parse(withoutPages)).toThrow();
    });

    it('should validate pagination field types', () => {
      expect(() => paginatedResponseSchema.parse({ ...validPaginatedResponse, total: 'not-a-number' })).toThrow();
      expect(() => paginatedResponseSchema.parse({ ...validPaginatedResponse, page: -1 })).toThrow();
      expect(() => paginatedResponseSchema.parse({ ...validPaginatedResponse, size: 0 })).toThrow();
    });

    it('should accept empty items array', () => {
      const emptyResponse = { ...validPaginatedResponse, items: [], total: 0 };
      expect(() => paginatedResponseSchema.parse(emptyResponse)).not.toThrow();
    });
  });

  describe('webSocketMessageSchema', () => {
    const validWebSocketMessage = {
      type: 'test-message',
      timestamp: '2023-01-01T00:00:00Z',
      data: { key: 'value' },
    };

    it('should validate valid WebSocket message', () => {
      const result = webSocketMessageSchema.parse(validWebSocketMessage);
      expect(result).toEqual(validWebSocketMessage);
    });

    it('should require type field', () => {
      const { type, ...withoutType } = validWebSocketMessage;
      expect(() => webSocketMessageSchema.parse(withoutType)).toThrow();
    });

    it('should accept messages without data', () => {
      const { data, ...withoutData } = validWebSocketMessage;
      expect(() => webSocketMessageSchema.parse(withoutData)).not.toThrow();
    });

    it('should accept messages without timestamp', () => {
      const { timestamp, ...withoutTimestamp } = validWebSocketMessage;
      expect(() => webSocketMessageSchema.parse(withoutTimestamp)).not.toThrow();
    });

    it('should accept various data types', () => {
      const messageWithString = { ...validWebSocketMessage, data: 'string-data' };
      expect(() => webSocketMessageSchema.parse(messageWithString)).not.toThrow();

      const messageWithNumber = { ...validWebSocketMessage, data: 42 };
      expect(() => webSocketMessageSchema.parse(messageWithNumber)).not.toThrow();

      const messageWithArray = { ...validWebSocketMessage, data: [1, 2, 3] };
      expect(() => webSocketMessageSchema.parse(messageWithArray)).not.toThrow();
    });
  });

  describe('validateApiResponse', () => {
    const testSchema = z.object({
      id: z.number(),
      name: z.string(),
    });

    it('should validate and return valid data', () => {
      const validData = { id: 1, name: 'test' };
      const result = validateApiResponse(validData, testSchema);
      expect(result).toEqual(validData);
    });

    it('should throw error for invalid data', () => {
      const invalidData = { id: 'not-a-number', name: 'test' };
      
      expect(() => validateApiResponse(invalidData, testSchema)).toThrow('Invalid API response');
      expect(mockLogger.error).toHaveBeenCalledWith(
        'API response validation failed',
        expect.any(z.ZodError),
        expect.objectContaining({ errors: expect.any(Array) })
      );
    });

    it('should handle non-Zod errors', () => {
      const mockSchema = {
        parse: jest.fn(() => {
          throw new Error('Non-Zod error');
        }),
      } as any;

      expect(() => validateApiResponse({ test: 'data' }, mockSchema)).toThrow('Non-Zod error');
    });

    it('should provide detailed error messages', () => {
      const invalidData = { id: 'string', name: 123 };
      
      try {
        validateApiResponse(invalidData, testSchema);
        fail('Should have thrown an error');
      } catch (error) {
        expect(error.message).toContain('Invalid API response');
      }
    });
  });

  describe('safeParseWebSocketMessage', () => {
    it('should return valid WebSocket message', () => {
      const validMessage = {
        type: 'test-message',
        timestamp: '2023-01-01T00:00:00Z',
        data: { key: 'value' },
      };

      const result = safeParseWebSocketMessage(validMessage);
      expect(result).toEqual(validMessage);
    });

    it('should return null for invalid message', () => {
      const invalidMessage = { invalid: 'message' };

      const result = safeParseWebSocketMessage(invalidMessage);
      expect(result).toBeNull();
      expect(mockLogger.error).toHaveBeenCalledWith(
        'WebSocket message validation failed',
        undefined,
        expect.objectContaining({ errors: expect.any(Array) })
      );
    });

    it('should handle null and undefined input', () => {
      expect(safeParseWebSocketMessage(null)).toBeNull();
      expect(safeParseWebSocketMessage(undefined)).toBeNull();
    });

    it('should handle non-object input', () => {
      expect(safeParseWebSocketMessage('string')).toBeNull();
      expect(safeParseWebSocketMessage(123)).toBeNull();
      expect(safeParseWebSocketMessage(true)).toBeNull();
    });
  });

  describe('edge cases and error conditions', () => {
    it('should handle deeply nested objects in sanitization', () => {
      const deepObject = {
        level1: {
          level2: {
            level3: {
              value: '  <script>deep xss</script>  ',
            },
          },
        },
      };

      const result = sanitizeObject(deepObject);
      expect(result.level1.level2.level3.value).toBe('deep xss');
    });

    it('should handle circular references in sanitization', () => {
      const circular: any = { name: '  test  ' };
      circular.self = circular;

      // This should not crash
      expect(() => sanitizeObject(circular)).not.toThrow();
    });

    it('should handle large arrays in sanitization', () => {
      const largeArray = Array(1000).fill('  test  ');
      const obj = { items: largeArray };

      const result = sanitizeObject(obj);
      expect(result.items[0]).toBe('test');
      expect(result.items[999]).toBe('test');
    });

    it('should handle special characters in strings', () => {
      const specialChars = 'emoji: 🚀, unicode: \u{1F600}, newlines: \n\r\t';
      const result = sanitizeString(specialChars);
      expect(result).toBe(specialChars); // Should preserve these
    });

    it('should handle malformed timestamps', () => {
      const invalidInstance = {
        id: 1,
        instance_id: 'inst-123',
        issue_id: 'ISSUE-456',
        status: 'running',
        branch: 'main',
        workspace_path: '/workspace/path',
        created_at: 'not-a-date',
        updated_at: '2023-01-01T01:00:00Z',
        metadata: {},
      };

      expect(() => instanceSchema.parse(invalidInstance)).toThrow();
    });
  });
});