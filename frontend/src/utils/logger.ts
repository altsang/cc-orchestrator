// Production-ready logging utility for CC-Orchestrator Frontend

import { environment } from '../config/environment';

export enum LogLevel {
  DEBUG = 0,
  INFO = 1,
  WARN = 2,
  ERROR = 3,
}

interface LogEntry {
  level: LogLevel;
  message: string;
  timestamp: string;
  data?: any;
  error?: Error;
}

class Logger {
  private minLevel: LogLevel;

  constructor() {
    // Set log level based on environment
    this.minLevel = environment === 'production' ? LogLevel.WARN : LogLevel.DEBUG;
  }

  private shouldLog(level: LogLevel): boolean {
    return level >= this.minLevel;
  }

  private formatMessage(level: LogLevel, message: string, data?: any): string {
    const timestamp = new Date().toISOString();
    const levelStr = LogLevel[level];
    
    if (data) {
      return `[${timestamp}] ${levelStr}: ${message} ${JSON.stringify(data)}`;
    }
    
    return `[${timestamp}] ${levelStr}: ${message}`;
  }

  private log(level: LogLevel, message: string, data?: any, error?: Error): void {
    if (!this.shouldLog(level)) {
      return;
    }

    const logEntry: LogEntry = {
      level,
      message,
      timestamp: new Date().toISOString(),
      data,
      error,
    };

    // In development, use console for immediate feedback
    if (environment === 'development') {
      switch (level) {
        case LogLevel.DEBUG:
          console.debug(this.formatMessage(level, message, data), error || '');
          break;
        case LogLevel.INFO:
          console.info(this.formatMessage(level, message, data), error || '');
          break;
        case LogLevel.WARN:
          console.warn(this.formatMessage(level, message, data), error || '');
          break;
        case LogLevel.ERROR:
          console.error(this.formatMessage(level, message, data), error || '');
          break;
      }
    }

    // In production, send to logging service
    if (environment === 'production' && level >= LogLevel.ERROR) {
      this.sendToLoggingService(logEntry);
    }
  }

  private sendToLoggingService(logEntry: LogEntry): void {
    // Placeholder for production logging service integration
    // Examples: Sentry, LogRocket, DataDog, CloudWatch, etc.
    
    // For now, we'll store critical errors for debugging
    try {
      const errorLog = {
        timestamp: logEntry.timestamp,
        level: LogLevel[logEntry.level],
        message: logEntry.message,
        data: logEntry.data,
        error: logEntry.error ? {
          message: logEntry.error.message,
          stack: logEntry.error.stack,
        } : undefined,
        userAgent: navigator.userAgent,
        url: window.location.href,
      };

      // Store in localStorage for debugging (limited storage)
      const existingLogs = JSON.parse(localStorage.getItem('cc_error_logs') || '[]');
      const newLogs = [errorLog, ...existingLogs.slice(0, 9)]; // Keep last 10 errors
      localStorage.setItem('cc_error_logs', JSON.stringify(newLogs));
      
    } catch (storageError) {
      // Fallback if localStorage fails
      console.error('Failed to store error log:', storageError);
    }
  }

  debug(message: string, data?: any): void {
    this.log(LogLevel.DEBUG, message, data);
  }

  info(message: string, data?: any): void {
    this.log(LogLevel.INFO, message, data);
  }

  warn(message: string, data?: any, error?: Error): void {
    this.log(LogLevel.WARN, message, data, error);
  }

  error(message: string, error?: Error, data?: any): void {
    this.log(LogLevel.ERROR, message, data, error);
  }

  // Specialized logging methods for common use cases
  apiRequest(method: string, url: string): void {
    this.debug(`API Request: ${method.toUpperCase()} ${url}`);
  }

  apiResponse(status: number, url: string): void {
    this.debug(`API Response: ${status} ${url}`);
  }

  apiError(message: string, error: Error, url?: string): void {
    this.error(`API Error${url ? ` for ${url}` : ''}: ${message}`, error);
  }

  websocketEvent(event: string, data?: any): void {
    this.debug(`WebSocket Event: ${event}`, data);
  }

  websocketError(message: string, error: Error | Event): void {
    this.error(`WebSocket Error: ${message}`, error instanceof Error ? error : new Error('WebSocket error'));
  }

  componentError(componentName: string, error: Error, errorInfo?: any): void {
    this.error(`Component Error in ${componentName}`, error, errorInfo);
  }
}

// Export singleton instance
export const logger = new Logger();
export default logger;