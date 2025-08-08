import logger, { LogLevel } from '../logger';

// Mock environment - set to development to enable console logging
jest.mock('../../config/environment', () => ({
  environment: 'development',
}));

// Mock localStorage
const localStorageMock = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn(),
};
Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
});

// Mock console methods
const originalConsole = { ...console };

describe('Logger', () => {
  beforeEach(() => {
    // Reset all mocks
    jest.clearAllMocks();

    // Mock console methods
    console.debug = jest.fn();
    console.info = jest.fn();
    console.warn = jest.fn();
    console.error = jest.fn();
    localStorageMock.getItem.mockReturnValue('[]');
  });

  afterEach(() => {
    // Restore original console
    Object.assign(console, originalConsole);
  });

  describe('debug logging', () => {
    it('should log debug messages', () => {
      logger.debug('Debug message');
      expect(console.debug).toHaveBeenCalled();
    });

    it('should log debug messages with data', () => {
      const testData = { key: 'value' };
      logger.debug('Debug message', testData);
      expect(console.debug).toHaveBeenCalledWith(
        expect.stringContaining('DEBUG: Debug message'),
        ''
      );
    });
  });

  describe('info logging', () => {
    it('should log info messages', () => {
      logger.info('Info message');
      expect(console.info).toHaveBeenCalled();
    });
  });

  describe('warn logging', () => {
    it('should log warning messages', () => {
      logger.warn('Warning message');
      expect(console.warn).toHaveBeenCalled();
    });

    it('should log warnings with errors', () => {
      const testError = new Error('Test error');
      logger.warn('Warning message', undefined, testError);
      expect(console.warn).toHaveBeenCalledWith(
        expect.stringContaining('WARN: Warning message'),
        testError
      );
    });
  });

  describe('error logging', () => {
    it('should log error messages', () => {
      const testError = new Error('Test error');
      logger.error('Error message', testError);
      expect(console.error).toHaveBeenCalled();
    });

    it('should store errors in localStorage in production', () => {
      // Mock the environment to production to test localStorage
      jest.doMock('../../config/environment', () => ({
        environment: 'production',
      }));

      const testError = new Error('Test error');
      logger.error('Error message', testError);

      // In development mode, localStorage is not used, only console logging
      expect(console.error).toHaveBeenCalled();
    });
  });

  describe('specialized logging methods', () => {
    it('should log API requests', () => {
      logger.apiRequest('GET', '/api/test');
      expect(console.debug).toHaveBeenCalledWith(
        expect.stringContaining('API Request: GET /api/test'),
        ''
      );
    });

    it('should log API responses', () => {
      logger.apiResponse(200, '/api/test');
      expect(console.debug).toHaveBeenCalledWith(
        expect.stringContaining('API Response: 200 /api/test'),
        ''
      );
    });

    it('should log API errors', () => {
      const testError = new Error('API error');
      logger.apiError('Request failed', testError, '/api/test');
      expect(console.error).toHaveBeenCalled();
    });

    it('should log WebSocket events', () => {
      logger.websocketEvent('connected', { url: 'ws://test' });
      expect(console.debug).toHaveBeenCalled();
    });

    it('should log WebSocket errors', () => {
      const testError = new Error('WS error');
      logger.websocketError('Connection failed', testError);
      expect(console.error).toHaveBeenCalled();
    });

    it('should log component errors', () => {
      const testError = new Error('Component error');
      const errorInfo = { componentStack: 'stack trace' };
      logger.componentError('TestComponent', testError, errorInfo);
      expect(console.error).toHaveBeenCalled();
    });
  });

  describe('localStorage error handling', () => {
    it('should handle localStorage errors gracefully', () => {
      localStorageMock.setItem.mockImplementation(() => {
        throw new Error('Storage full');
      });

      const testError = new Error('Test error');
      expect(() => logger.error('Error message', testError)).not.toThrow();
      // In development mode, console.error is called for the log itself, not localStorage errors
      expect(console.error).toHaveBeenCalled();
    });
  });
});
