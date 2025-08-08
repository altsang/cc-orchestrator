// Zod schemas for API response validation and input sanitization

import { z } from 'zod';

// Base schemas
export const idSchema = z.number().int().positive();
export const timestampSchema = z.string().datetime();

// Instance schemas
export const instanceStatusSchema = z.enum(['initializing', 'running', 'stopped', 'failed', 'terminating']);
export const healthStatusSchema = z.enum(['healthy', 'degraded', 'unhealthy', 'unknown']);

export const instanceSchema = z.object({
  id: idSchema,
  issue_id: z.string().min(1).max(100),
  status: instanceStatusSchema,
  health_status: healthStatusSchema,
  branch_name: z.string().min(1).max(255),
  workspace_path: z.string().min(1).max(500),
  created_at: timestampSchema,
  updated_at: timestampSchema,
  extra_metadata: z.record(z.any()).default({}),
  health_check_count: z.number().int().min(0),
  healthy_check_count: z.number().int().min(0),
  recovery_attempt_count: z.number().int().min(0),
});

// Task schemas
export const taskStatusSchema = z.enum(['pending', 'in_progress', 'completed', 'cancelled']);
export const taskPrioritySchema = z.enum(['low', 'medium', 'high', 'urgent']);

export const taskSchema = z.object({
  id: idSchema,
  title: z.string().min(1).max(255),
  status: taskStatusSchema,
  priority: taskPrioritySchema,
  instance_id: idSchema.optional(),
  requirements: z.record(z.any()).default({}),
  results: z.record(z.any()).default({}),
  extra_metadata: z.record(z.any()).default({}),
  created_at: timestampSchema,
  updated_at: timestampSchema,
});

// WebSocket message schemas
export const webSocketMessageSchema = z.object({
  type: z.string().min(1),
  data: z.any(),
  timestamp: timestampSchema.optional(),
  message_id: z.string().uuid().optional(),
});

export const instanceUpdateSchema = z.object({
  type: z.literal('instance_update'),
  data: instanceSchema,
});

export const taskUpdateSchema = z.object({
  type: z.literal('task_update'),
  data: taskSchema,
});

export const alertMessageSchema = z.object({
  type: z.literal('alert'),
  data: z.object({
    id: idSchema,
    level: z.enum(['info', 'warning', 'error', 'critical']),
    message: z.string().min(1).max(1000),
    created_at: timestampSchema,
  }),
});

// API response schemas
export const apiResponseSchema = z.object({
  success: z.boolean(),
  message: z.string().optional(),
  data: z.any().optional(),
});

export const paginatedResponseSchema = z.object({
  items: z.array(z.any()),
  total: z.number().int().min(0),
  page: z.number().int().min(1),
  size: z.number().int().min(1),
  pages: z.number().int().min(0),
});

// Input sanitization functions
export const sanitizeString = (input: string): string => {
  return input
    .trim()
    .replace(/[<>]/g, '') // Remove potential HTML tags
    .slice(0, 1000); // Limit length
};

export const sanitizeObject = <T extends Record<string, any>>(obj: T): T => {
  const sanitized = { ...obj };

  Object.keys(sanitized).forEach(key => {
    const value = sanitized[key];
    if (typeof value === 'string') {
      sanitized[key] = sanitizeString(value);
    } else if (value && typeof value === 'object' && !Array.isArray(value)) {
      sanitized[key] = sanitizeObject(value);
    }
  });

  return sanitized;
};

// Validation helper functions
export const validateApiResponse = <T>(data: unknown, schema: z.ZodSchema<T>): T => {
  try {
    return schema.parse(data);
  } catch (error) {
    if (error instanceof z.ZodError) {
      console.error('API response validation failed:', error.errors);
      throw new Error(`Invalid API response: ${error.errors.map(e => e.message).join(', ')}`);
    }
    throw error;
  }
};

export const safeParseWebSocketMessage = (data: unknown) => {
  const result = webSocketMessageSchema.safeParse(data);
  if (!result.success) {
    console.error('WebSocket message validation failed:', result.error.errors);
    return null;
  }
  return result.data;
};
