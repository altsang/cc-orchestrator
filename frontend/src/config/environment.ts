// Environment configuration with validation and secure defaults

import logger from '../utils/logger';

export interface EnvironmentConfig {
  apiBaseUrl: string;
  wsBaseUrl: string;
  environment: 'development' | 'staging' | 'production';
  apiTimeout: number;
  wsReconnectInterval: number;
  wsMaxReconnectAttempts: number;
}

const validateUrl = (url: string, name: string): string => {
  if (!url) {
    throw new Error(`${name} is required but not provided`);
  }

  try {
    new URL(url);
    return url;
  } catch (error) {
    throw new Error(`Invalid ${name}: ${url}`);
  }
};

const validateEnvironment = (env: string): 'development' | 'staging' | 'production' => {
  if (!env || !['development', 'staging', 'production'].includes(env)) {
    logger.warn(`Invalid environment '${env}', defaulting to 'development'`);
    return 'development';
  }
  return env as 'development' | 'staging' | 'production';
};

const validateNumber = (value: string | undefined, defaultValue: number, min: number, max: number, name: string): number => {
  if (!value) return defaultValue;

  const parsed = parseInt(value, 10);
  if (isNaN(parsed) || parsed < min || parsed > max) {
    logger.warn(`Invalid ${name} '${value}', using default: ${defaultValue}`);
    return defaultValue;
  }
  return parsed;
};

// Load and validate environment configuration
const loadEnvironmentConfig = (): EnvironmentConfig => {
  const config: EnvironmentConfig = {
    apiBaseUrl: validateUrl(
      process.env.REACT_APP_API_BASE_URL || 'http://localhost:8080/api/v1',
      'API Base URL'
    ),
    wsBaseUrl: validateUrl(
      process.env.REACT_APP_WS_BASE_URL || 'ws://localhost:8080/ws',
      'WebSocket Base URL'
    ),
    environment: validateEnvironment(process.env.REACT_APP_ENV || 'development'),
    apiTimeout: validateNumber(process.env.REACT_APP_API_TIMEOUT, 10000, 1000, 60000, 'API Timeout'),
    wsReconnectInterval: validateNumber(process.env.REACT_APP_WS_RECONNECT_INTERVAL, 3000, 1000, 30000, 'WebSocket Reconnect Interval'),
    wsMaxReconnectAttempts: validateNumber(process.env.REACT_APP_WS_MAX_RECONNECT_ATTEMPTS, 5, 1, 20, 'WebSocket Max Reconnect Attempts'),
  };

  // Security validation for production
  if (config.environment === 'production') {
    if (config.apiBaseUrl.includes('localhost') || config.wsBaseUrl.includes('localhost')) {
      throw new Error('Production environment cannot use localhost URLs');
    }

    if (!config.apiBaseUrl.startsWith('https://')) {
      logger.warn('Production API should use HTTPS for security');
    }

    if (!config.wsBaseUrl.startsWith('wss://')) {
      logger.warn('Production WebSocket should use WSS for security');
    }
  }

  return config;
};

// Export validated configuration
export const environmentConfig = loadEnvironmentConfig();

// Export individual values for convenience
export const {
  apiBaseUrl,
  wsBaseUrl,
  environment,
  apiTimeout,
  wsReconnectInterval,
  wsMaxReconnectAttempts
} = environmentConfig;
