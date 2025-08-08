import logger from '../../utils/logger';

// Mock logger before importing environment
jest.mock('../../utils/logger', () => ({
  warn: jest.fn(),
}));

// Mock process.env
const mockProcessEnv = {
  REACT_APP_API_BASE_URL: 'https://api.example.com/api/v1',
  REACT_APP_WS_BASE_URL: 'wss://api.example.com/ws',
  REACT_APP_ENV: 'production',
  REACT_APP_API_TIMEOUT: '15000',
  REACT_APP_WS_RECONNECT_INTERVAL: '5000',
  REACT_APP_WS_MAX_RECONNECT_ATTEMPTS: '10',
};

describe('Environment Configuration', () => {
  let originalProcessEnv: typeof process.env;

  beforeEach(() => {
    originalProcessEnv = process.env;
    jest.clearAllMocks();
    
    // Clear the module cache to get fresh imports
    jest.resetModules();
  });

  afterEach(() => {
    process.env = originalProcessEnv;
  });

  it('should load valid configuration', () => {
    process.env = { ...mockProcessEnv };
    
    const { environmentConfig } = require('../../environment');
    
    expect(environmentConfig.apiBaseUrl).toBe('https://api.example.com/api/v1');
    expect(environmentConfig.wsBaseUrl).toBe('wss://api.example.com/ws');
    expect(environmentConfig.environment).toBe('production');
    expect(environmentConfig.apiTimeout).toBe(15000);
    expect(environmentConfig.wsReconnectInterval).toBe(5000);
    expect(environmentConfig.wsMaxReconnectAttempts).toBe(10);
  });

  it('should use defaults when environment variables are not set', () => {
    process.env = {};
    
    const { environmentConfig } = require('../../environment');
    
    expect(environmentConfig.apiBaseUrl).toBe('http://localhost:8080/api/v1');
    expect(environmentConfig.wsBaseUrl).toBe('ws://localhost:8080/ws');
    expect(environmentConfig.environment).toBe('development');
    expect(environmentConfig.apiTimeout).toBe(10000);
    expect(environmentConfig.wsReconnectInterval).toBe(3000);
    expect(environmentConfig.wsMaxReconnectAttempts).toBe(5);
  });

  it('should warn about invalid environment values', () => {
    process.env = {
      ...mockProcessEnv,
      REACT_APP_ENV: 'invalid-env',
      REACT_APP_API_TIMEOUT: 'invalid-number',
    };
    
    require('../../environment');
    
    expect(logger.warn).toHaveBeenCalledWith(
      "Invalid environment 'invalid-env', defaulting to 'development'"
    );
    expect(logger.warn).toHaveBeenCalledWith(
      "Invalid API Timeout 'invalid-number', using default: 10000"
    );
  });

  it('should throw error for invalid URLs', () => {
    process.env = {
      ...mockProcessEnv,
      REACT_APP_API_BASE_URL: 'invalid-url',
    };
    
    expect(() => require('../../environment')).toThrow('Invalid API Base URL: invalid-url');
  });

  it('should warn about insecure production URLs', () => {
    process.env = {
      ...mockProcessEnv,
      REACT_APP_ENV: 'production',
      REACT_APP_API_BASE_URL: 'http://api.example.com/api/v1',
      REACT_APP_WS_BASE_URL: 'ws://api.example.com/ws',
    };
    
    require('../../environment');
    
    expect(logger.warn).toHaveBeenCalledWith(
      'Production API should use HTTPS for security'
    );
    expect(logger.warn).toHaveBeenCalledWith(
      'Production WebSocket should use WSS for security'
    );
  });

  it('should throw error for localhost URLs in production', () => {
    process.env = {
      ...mockProcessEnv,
      REACT_APP_ENV: 'production',
      REACT_APP_API_BASE_URL: 'https://localhost:8080/api/v1',
    };
    
    expect(() => require('../../environment')).toThrow(
      'Production environment cannot use localhost URLs'
    );
  });

  it('should validate number ranges', () => {
    process.env = {
      ...mockProcessEnv,
      REACT_APP_API_TIMEOUT: '100000', // Above max
      REACT_APP_WS_RECONNECT_INTERVAL: '500', // Below min
      REACT_APP_WS_MAX_RECONNECT_ATTEMPTS: '25', // Above max
    };
    
    require('../../environment');
    
    expect(logger.warn).toHaveBeenCalledWith(
      "Invalid API Timeout '100000', using default: 10000"
    );
    expect(logger.warn).toHaveBeenCalledWith(
      "Invalid WebSocket Reconnect Interval '500', using default: 3000"
    );
    expect(logger.warn).toHaveBeenCalledWith(
      "Invalid WebSocket Max Reconnect Attempts '25', using default: 5"
    );
  });

  it('should export individual configuration values', () => {
    process.env = { ...mockProcessEnv };
    
    const {
      apiBaseUrl,
      wsBaseUrl,
      environment,
      apiTimeout,
      wsReconnectInterval,
      wsMaxReconnectAttempts
    } = require('../../environment');
    
    expect(apiBaseUrl).toBe('https://api.example.com/api/v1');
    expect(wsBaseUrl).toBe('wss://api.example.com/ws');
    expect(environment).toBe('production');
    expect(apiTimeout).toBe(15000);
    expect(wsReconnectInterval).toBe(5000);
    expect(wsMaxReconnectAttempts).toBe(10);
  });
});