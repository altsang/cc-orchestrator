// Comprehensive tests for LogViewer component

import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';
import LogViewer from '../LogViewer';
import { LogEntry, LogLevel, LogEntryType, WebSocketMessage } from '../../types';
import * as apiService from '../../services/api';
import * as websocketHook from '../../hooks/useWebSocket';

// Mock dependencies
vi.mock('../../services/api');
vi.mock('../../hooks/useWebSocket');
vi.mock('../../utils/logger');

// Mock react-window for testing
vi.mock('react-window', () => ({
  FixedSizeList: ({ children, itemCount, itemData }: any) => {
    const items = [];
    for (let i = 0; i < Math.min(itemCount, 10); i++) {
      items.push(
        React.createElement('div',
          { key: i, 'data-testid': `log-row-${i}` },
          children({ index: i, style: {}, data: itemData })
        )
      );
    }
    return React.createElement('div', { 'data-testid': 'virtual-list' }, items);
  },
}));

const mockSearchLogs = vi.mocked(apiService.searchLogs);
const mockExportLogs = vi.mocked(apiService.exportLogs);
const mockStartLogStream = vi.mocked(apiService.startLogStream);
const mockStopLogStream = vi.mocked(apiService.stopLogStream);
const mockUseLogsWebSocket = vi.mocked(websocketHook.useLogsWebSocket);

// Sample log entries for testing
const sampleLogs: LogEntry[] = [
  {
    id: 'log_1',
    timestamp: '2023-10-01T10:00:00Z',
    level: LogLevel.INFO,
    logger: 'test.logger',
    message: 'Test info message',
    module: 'test_module',
    function: 'test_function',
    line: 42,
    context: LogEntryType.SYSTEM,
    metadata: { test: 'data' },
  },
  {
    id: 'log_2',
    timestamp: '2023-10-01T10:01:00Z',
    level: LogLevel.ERROR,
    logger: 'error.logger',
    message: 'Test error message with exception',
    context: LogEntryType.WEB,
    instance_id: 'instance_123',
    exception: {
      type: 'ValueError',
      message: 'Test exception',
      traceback: ['Traceback line 1', 'Traceback line 2'],
    },
  },
  {
    id: 'log_3',
    timestamp: '2023-10-01T10:02:00Z',
    level: LogLevel.DEBUG,
    logger: 'debug.logger',
    message: 'Debug message for testing search functionality',
    context: LogEntryType.TASK,
    task_id: 'task_456',
  },
];

describe('LogViewer Component', () => {
  const mockWebSocketHook = {
    isConnected: true,
    subscribe: vi.fn(),
    unsubscribe: vi.fn(),
    connect: vi.fn(),
    disconnect: vi.fn(),
    send: vi.fn(),
    lastMessage: null,
  };

  beforeEach(() => {
    // Reset all mocks
    vi.clearAllMocks();

    // Setup default mock implementations
    mockUseLogsWebSocket.mockReturnValue(mockWebSocketHook);
    mockSearchLogs.mockResolvedValue({
      entries: sampleLogs,
      total_count: 3,
      has_more: false,
      search_duration_ms: 50,
    });
    mockStartLogStream.mockResolvedValue({
      stream_id: 'test_stream_123',
      status: 'started',
    });
    mockStopLogStream.mockResolvedValue({
      stream_id: 'test_stream_123',
      status: 'stopped',
    });
  });

  afterEach(() => {
    vi.clearAllTimers();
  });

  describe('Rendering', () => {
    it('renders log viewer with header and controls', () => {
      render(<LogViewer />);

      expect(screen.getByText('Log Viewer')).toBeInTheDocument();
      expect(screen.getByText('Connected')).toBeInTheDocument();
      expect(screen.getByText('Start Stream')).toBeInTheDocument();
      expect(screen.getByText('Auto-scroll')).toBeInTheDocument();
    });

    it('renders search controls when showSearch is true', () => {
      render(<LogViewer showSearch={true} />);

      expect(screen.getByPlaceholderText('Search logs...')).toBeInTheDocument();
      expect(screen.getByText('Regex')).toBeInTheDocument();
      expect(screen.getByText('Case')).toBeInTheDocument();
      expect(screen.getByText('Levels:')).toBeInTheDocument();
      expect(screen.getByText('Contexts:')).toBeInTheDocument();
    });

    it('renders export controls when showExport is true', () => {
      render(<LogViewer showExport={true} />);

      expect(screen.getByText('Export:')).toBeInTheDocument();
      expect(screen.getByDisplayValue('json')).toBeInTheDocument();
      expect(screen.getByText('Export')).toBeInTheDocument();
    });

    it('shows disconnected status when WebSocket is not connected', () => {
      mockUseLogsWebSocket.mockReturnValue({
        ...mockWebSocketHook,
        isConnected: false,
      });

      render(<LogViewer />);

      expect(screen.getByText('Disconnected')).toBeInTheDocument();
    });
  });

  describe('Search Functionality', () => {
    it('performs search when search button is clicked', async () => {
      const user = userEvent.setup();
      render(<LogViewer showSearch={true} />);

      const searchInput = screen.getByPlaceholderText('Search logs...');
      const searchButton = screen.getByText('Search');

      await user.type(searchInput, 'error');
      await user.click(searchButton);

      await waitFor(() => {
        expect(mockSearchLogs).toHaveBeenCalledWith(expect.objectContaining({
          query: 'error',
          limit: 5000,
        }));
      });
    });

    it('performs search when Enter key is pressed', async () => {
      const user = userEvent.setup();
      render(<LogViewer showSearch={true} />);

      const searchInput = screen.getByPlaceholderText('Search logs...');

      await user.type(searchInput, 'test{enter}');

      await waitFor(() => {
        expect(mockSearchLogs).toHaveBeenCalledWith(expect.objectContaining({
          query: 'test',
        }));
      });
    });

    it('toggles regex search option', async () => {
      const user = userEvent.setup();
      render(<LogViewer showSearch={true} />);

      const regexCheckbox = screen.getByLabelText('Regex');
      await user.click(regexCheckbox);

      const searchButton = screen.getByText('Search');
      await user.click(searchButton);

      await waitFor(() => {
        expect(mockSearchLogs).toHaveBeenCalledWith(expect.objectContaining({
          regex_enabled: true,
        }));
      });
    });

    it('toggles case sensitive search option', async () => {
      const user = userEvent.setup();
      render(<LogViewer showSearch={true} />);

      const caseCheckbox = screen.getByLabelText('Case');
      await user.click(caseCheckbox);

      const searchButton = screen.getByText('Search');
      await user.click(searchButton);

      await waitFor(() => {
        expect(mockSearchLogs).toHaveBeenCalledWith(expect.objectContaining({
          case_sensitive: true,
        }));
      });
    });
  });

  describe('Export Functionality', () => {
    it('exports logs in JSON format', async () => {
      const user = userEvent.setup();
      render(<LogViewer showExport={true} />);

      const exportButton = screen.getByText('Export');
      await user.click(exportButton);

      await waitFor(() => {
        expect(mockExportLogs).toHaveBeenCalledWith(expect.objectContaining({
          format: 'json',
          include_metadata: true,
        }));
      });
    });

    it('exports logs in CSV format', async () => {
      const user = userEvent.setup();
      render(<LogViewer showExport={true} />);

      const formatSelect = screen.getByDisplayValue('json');
      await user.selectOptions(formatSelect, 'csv');

      const exportButton = screen.getByText('Export');
      await user.click(exportButton);

      await waitFor(() => {
        expect(mockExportLogs).toHaveBeenCalledWith(expect.objectContaining({
          format: 'csv',
        }));
      });
    });
  });

  describe('WebSocket Integration', () => {
    it('handles incoming log messages', async () => {
      const messageHandler = vi.fn();
      mockUseLogsWebSocket.mockImplementation((handler) => {
        messageHandler.mockImplementation(handler || (() => {}));
        return mockWebSocketHook;
      });

      render(<LogViewer />);

      // Simulate incoming log message
      const logMessage: WebSocketMessage = {
        type: 'log_entry',
        data: sampleLogs[0],
        timestamp: '2023-10-01T10:00:00Z',
      };

      act(() => {
        messageHandler(logMessage);
      });

      await waitFor(() => {
        expect(screen.getByTestId('virtual-list')).toBeInTheDocument();
      });
    });

    it('starts log streaming when start button is clicked', async () => {
      const user = userEvent.setup();
      render(<LogViewer />);

      const startButton = screen.getByText('Start Stream');
      await user.click(startButton);

      await waitFor(() => {
        expect(mockStartLogStream).toHaveBeenCalledWith(expect.objectContaining({
          buffer_size: 100,
        }));
      });
    });
  });

  describe('Error Handling', () => {
    it('handles search errors gracefully', async () => {
      const user = userEvent.setup();
      mockSearchLogs.mockRejectedValue(new Error('Search failed'));

      render(<LogViewer showSearch={true} />);

      const searchButton = screen.getByText('Search');
      await user.click(searchButton);

      await waitFor(() => {
        expect(mockSearchLogs).toHaveBeenCalled();
      });
    });

    it('handles export errors gracefully', async () => {
      const user = userEvent.setup();
      mockExportLogs.mockRejectedValue(new Error('Export failed'));

      render(<LogViewer showExport={true} />);

      const exportButton = screen.getByText('Export');
      await user.click(exportButton);

      await waitFor(() => {
        expect(mockExportLogs).toHaveBeenCalled();
        expect(screen.getByText('Export')).toBeInTheDocument();
      });
    });
  });

  describe('Accessibility', () => {
    it('has proper ARIA labels and roles', () => {
      render(<LogViewer showSearch={true} showExport={true} />);

      const searchInput = screen.getByPlaceholderText('Search logs...');
      expect(searchInput).toHaveAttribute('type', 'text');

      const buttons = screen.getAllByRole('button');
      expect(buttons.length).toBeGreaterThan(0);

      // Check checkboxes have proper labels
      const regexCheckbox = screen.getByRole('checkbox', { name: /regex/i });
      const caseCheckbox = screen.getByRole('checkbox', { name: /case/i });
      expect(regexCheckbox).toBeInTheDocument();
      expect(caseCheckbox).toBeInTheDocument();
    });
  });
});
