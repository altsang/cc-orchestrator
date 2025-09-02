// Real-time log viewer component with search, filtering, and export capabilities

import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { FixedSizeList as List } from 'react-window';
import {
  LogEntry,
  LogLevel,
  LogEntryType,
  LogSearchRequest,
  LogExportFormat,
  LogStreamFilter,
  WebSocketMessage
} from '../types';
import { useLogsWebSocket } from '../hooks/useWebSocket';
import { searchLogs, exportLogs, startLogStream, stopLogStream } from '../services/api';
import logger from '../utils/logger';

interface LogViewerProps {
  className?: string;
  height?: number;
  autoScroll?: boolean;
  showSearch?: boolean;
  showExport?: boolean;
  instanceId?: string;
  taskId?: string;
}

interface LogViewerState {
  logs: LogEntry[];
  filteredLogs: LogEntry[];
  searchQuery: string;
  selectedLevels: Set<LogLevel>;
  selectedContexts: Set<LogEntryType>;
  isSearching: boolean;
  isStreaming: boolean;
  streamId: string | null;
  showRegexSearch: boolean;
  caseSensitive: boolean;
  autoScroll: boolean;
  exportFormat: LogExportFormat;
  isExporting: boolean;
}

const LEVEL_COLORS = {
  [LogLevel.DEBUG]: 'text-gray-500',
  [LogLevel.INFO]: 'text-blue-600',
  [LogLevel.WARNING]: 'text-yellow-600',
  [LogLevel.ERROR]: 'text-red-600',
  [LogLevel.CRITICAL]: 'text-red-800 font-bold',
};

const LEVEL_BG_COLORS = {
  [LogLevel.DEBUG]: 'bg-gray-100',
  [LogLevel.INFO]: 'bg-blue-50',
  [LogLevel.WARNING]: 'bg-yellow-50',
  [LogLevel.ERROR]: 'bg-red-50',
  [LogLevel.CRITICAL]: 'bg-red-100',
};

export const LogViewer: React.FC<LogViewerProps> = ({
  className = '',
  height = 600,
  autoScroll: initialAutoScroll = true,
  showSearch = true,
  showExport = true,
  instanceId,
  taskId,
}) => {
  const listRef = useRef<List>(null);
  const scrollTimeoutRef = useRef<NodeJS.Timeout>();

  const [state, setState] = useState<LogViewerState>({
    logs: [],
    filteredLogs: [],
    searchQuery: '',
    selectedLevels: new Set(Object.values(LogLevel)),
    selectedContexts: new Set(Object.values(LogEntryType)),
    isSearching: false,
    isStreaming: false,
    streamId: null,
    showRegexSearch: false,
    caseSensitive: false,
    autoScroll: initialAutoScroll,
    exportFormat: LogExportFormat.JSON,
    isExporting: false,
  });

  // WebSocket message handler for real-time log entries
  const handleLogMessage = useCallback((message: WebSocketMessage) => {
    if (message.type === 'log_entry') {
      const logEntry = message.data as LogEntry;

      setState(prev => {
        const newLogs = [...prev.logs, logEntry];
        // Keep only the last 10,000 entries for performance
        if (newLogs.length > 10000) {
          newLogs.splice(0, newLogs.length - 10000);
        }

        return {
          ...prev,
          logs: newLogs,
        };
      });
    } else if (message.type === 'log_stream_started') {
      setState(prev => ({
        ...prev,
        isStreaming: true,
        streamId: message.data.stream_id,
      }));
      logger.websocketEvent('Log stream started', { streamId: message.data.stream_id });
    } else if (message.type === 'log_stream_stopped') {
      setState(prev => ({
        ...prev,
        isStreaming: false,
        streamId: null,
      }));
      logger.websocketEvent('Log stream stopped');
    }
  }, []);

  const { isConnected, subscribe, unsubscribe } = useLogsWebSocket(handleLogMessage);

  // Filter logs based on current criteria
  const filteredLogs = useMemo(() => {
    let filtered = state.logs;

    // Filter by levels
    if (state.selectedLevels.size < Object.values(LogLevel).length) {
      filtered = filtered.filter(log => state.selectedLevels.has(log.level));
    }

    // Filter by contexts
    if (state.selectedContexts.size < Object.values(LogEntryType).length) {
      filtered = filtered.filter(log =>
        log.context && state.selectedContexts.has(log.context)
      );
    }

    // Filter by instance ID
    if (instanceId) {
      filtered = filtered.filter(log => log.instance_id === instanceId);
    }

    // Filter by task ID
    if (taskId) {
      filtered = filtered.filter(log => log.task_id === taskId);
    }

    // Filter by search query
    if (state.searchQuery.trim()) {
      const query = state.caseSensitive ? state.searchQuery : state.searchQuery.toLowerCase();

      if (state.showRegexSearch) {
        try {
          const regex = new RegExp(query, state.caseSensitive ? 'g' : 'gi');
          filtered = filtered.filter(log => {
            const searchText = `${log.message} ${log.logger} ${log.module || ''} ${log.function || ''}`;
            return regex.test(searchText);
          });
        } catch (error) {
          // Invalid regex, fall back to literal search
          filtered = filtered.filter(log => {
            const searchText = state.caseSensitive
              ? `${log.message} ${log.logger} ${log.module || ''} ${log.function || ''}`
              : `${log.message} ${log.logger} ${log.module || ''} ${log.function || ''}`.toLowerCase();
            return searchText.includes(query);
          });
        }
      } else {
        filtered = filtered.filter(log => {
          const searchText = state.caseSensitive
            ? `${log.message} ${log.logger} ${log.module || ''} ${log.function || ''}`
            : `${log.message} ${log.logger} ${log.module || ''} ${log.function || ''}`.toLowerCase();
          return searchText.includes(query);
        });
      }
    }

    return filtered;
  }, [state.logs, state.selectedLevels, state.selectedContexts, state.searchQuery, state.caseSensitive, state.showRegexSearch, instanceId, taskId]);

  // Auto-scroll to bottom when new logs arrive
  useEffect(() => {
    if (state.autoScroll && filteredLogs.length > 0) {
      if (scrollTimeoutRef.current) {
        clearTimeout(scrollTimeoutRef.current);
      }
      scrollTimeoutRef.current = setTimeout(() => {
        listRef.current?.scrollToItem(filteredLogs.length - 1, 'end');
      }, 50);
    }
  }, [filteredLogs.length, state.autoScroll]);

  // Start log streaming
  const handleStartStreaming = useCallback(async () => {
    if (!isConnected) {
      logger.error('WebSocket not connected');
      return;
    }

    try {
      setState(prev => ({ ...prev, isStreaming: true }));

      const streamFilter: LogStreamFilter = {
        level: state.selectedLevels.size < Object.values(LogLevel).length
          ? Array.from(state.selectedLevels)
          : undefined,
        context: state.selectedContexts.size < Object.values(LogEntryType).length
          ? Array.from(state.selectedContexts)
          : undefined,
        instance_id: instanceId,
        task_id: taskId,
        buffer_size: 100,
      };

      const response = await startLogStream(streamFilter);
      setState(prev => ({
        ...prev,
        streamId: response.stream_id,
        isStreaming: true,
      }));

      logger.info('Log streaming started', { streamId: response.stream_id });
    } catch (error) {
      logger.error('Failed to start log streaming', error as Error);
      setState(prev => ({ ...prev, isStreaming: false }));
    }
  }, [isConnected, state.selectedLevels, state.selectedContexts, instanceId, taskId]);

  // Stop log streaming
  const handleStopStreaming = useCallback(async () => {
    if (!state.streamId) return;

    try {
      await stopLogStream(state.streamId);
      setState(prev => ({
        ...prev,
        isStreaming: false,
        streamId: null,
      }));
      logger.info('Log streaming stopped');
    } catch (error) {
      logger.error('Failed to stop log streaming', error as Error);
    }
  }, [state.streamId]);

  // Search logs
  const handleSearch = useCallback(async () => {
    setState(prev => ({ ...prev, isSearching: true }));

    try {
      const searchRequest: LogSearchRequest = {
        query: state.searchQuery.trim() || undefined,
        level: state.selectedLevels.size < Object.values(LogLevel).length
          ? Array.from(state.selectedLevels)
          : undefined,
        context: state.selectedContexts.size < Object.values(LogEntryType).length
          ? Array.from(state.selectedContexts)
          : undefined,
        instance_id: instanceId,
        task_id: taskId,
        regex_enabled: state.showRegexSearch,
        case_sensitive: state.caseSensitive,
        limit: 5000,
        offset: 0,
      };

      const response = await searchLogs(searchRequest);
      setState(prev => ({
        ...prev,
        logs: response.entries,
        isSearching: false,
      }));

      logger.info('Log search completed', {
        totalResults: response.total_count,
        searchDuration: response.search_duration_ms
      });
    } catch (error) {
      logger.error('Log search failed', error as Error);
      setState(prev => ({ ...prev, isSearching: false }));
    }
  }, [state.searchQuery, state.selectedLevels, state.selectedContexts, state.showRegexSearch, state.caseSensitive, instanceId, taskId]);

  // Export logs
  const handleExport = useCallback(async () => {
    setState(prev => ({ ...prev, isExporting: true }));

    try {
      const searchRequest: LogSearchRequest = {
        query: state.searchQuery.trim() || undefined,
        level: state.selectedLevels.size < Object.values(LogLevel).length
          ? Array.from(state.selectedLevels)
          : undefined,
        context: state.selectedContexts.size < Object.values(LogEntryType).length
          ? Array.from(state.selectedContexts)
          : undefined,
        instance_id: instanceId,
        task_id: taskId,
        regex_enabled: state.showRegexSearch,
        case_sensitive: state.caseSensitive,
        limit: 50000, // Higher limit for exports
        offset: 0,
      };

      await exportLogs({
        search: searchRequest,
        format: state.exportFormat,
        include_metadata: true,
      });

      logger.info('Log export completed', { format: state.exportFormat });
    } catch (error) {
      logger.error('Log export failed', error as Error);
    } finally {
      setState(prev => ({ ...prev, isExporting: false }));
    }
  }, [state.searchQuery, state.selectedLevels, state.selectedContexts, state.showRegexSearch, state.caseSensitive, state.exportFormat, instanceId, taskId]);

  // Toggle level filter
  const toggleLevel = useCallback((level: LogLevel) => {
    setState(prev => {
      const newLevels = new Set(prev.selectedLevels);
      if (newLevels.has(level)) {
        newLevels.delete(level);
      } else {
        newLevels.add(level);
      }
      return { ...prev, selectedLevels: newLevels };
    });
  }, []);

  // Toggle context filter
  const toggleContext = useCallback((context: LogEntryType) => {
    setState(prev => {
      const newContexts = new Set(prev.selectedContexts);
      if (newContexts.has(context)) {
        newContexts.delete(context);
      } else {
        newContexts.add(context);
      }
      return { ...prev, selectedContexts: newContexts };
    });
  }, []);

  // Log entry renderer for virtual list
  const LogEntryRow = useCallback(({ index, style }: { index: number; style: React.CSSProperties }) => {
    const log = filteredLogs[index];
    if (!log) return null;

    const timestamp = new Date(log.timestamp).toLocaleString();
    const levelColor = LEVEL_COLORS[log.level] || 'text-gray-600';
    const levelBg = LEVEL_BG_COLORS[log.level] || 'bg-gray-50';

    return (
      <div style={style} className={`px-3 py-2 border-b border-gray-100 ${levelBg} hover:bg-opacity-80`}>
        <div className="flex items-start space-x-2 text-sm font-mono">
          <span className="text-xs text-gray-500 shrink-0 w-32">{timestamp}</span>
          <span className={`font-semibold shrink-0 w-20 ${levelColor}`}>{log.level}</span>
          <span className="text-gray-600 shrink-0 w-24 truncate" title={log.logger}>
            {log.logger}
          </span>
          <span className="flex-1 text-gray-900 break-all">
            {log.message}
          </span>
          {log.context && (
            <span className="text-xs text-gray-400 shrink-0 px-1 py-0.5 bg-gray-200 rounded">
              {log.context}
            </span>
          )}
          {log.instance_id && (
            <span className="text-xs text-blue-600 shrink-0 px-1 py-0.5 bg-blue-100 rounded">
              I:{log.instance_id}
            </span>
          )}
          {log.task_id && (
            <span className="text-xs text-green-600 shrink-0 px-1 py-0.5 bg-green-100 rounded">
              T:{log.task_id}
            </span>
          )}
        </div>
        {log.exception && (
          <div className="mt-1 p-2 bg-red-100 border border-red-200 rounded text-xs">
            <div className="font-semibold text-red-800">{log.exception.type}: {log.exception.message}</div>
            {log.exception.traceback && (
              <pre className="mt-1 text-red-700 whitespace-pre-wrap">
                {Array.isArray(log.exception.traceback) ? log.exception.traceback.join('') : log.exception.traceback}
              </pre>
            )}
          </div>
        )}
      </div>
    );
  }, [filteredLogs]);

  return (
    <div className={`flex flex-col bg-white border border-gray-200 rounded-lg shadow-sm ${className}`}>
      {/* Header with controls */}
      <div className="p-4 border-b border-gray-200 bg-gray-50">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-lg font-semibold text-gray-900">Log Viewer</h3>
          <div className="flex items-center space-x-2">
            {/* Connection status */}
            <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`}></div>
            <span className="text-sm text-gray-600">
              {isConnected ? 'Connected' : 'Disconnected'}
            </span>

            {/* Stream controls */}
            {isConnected && (
              <>
                {!state.isStreaming ? (
                  <button
                    onClick={handleStartStreaming}
                    className="px-3 py-1 text-sm bg-green-600 text-white rounded hover:bg-green-700"
                  >
                    Start Stream
                  </button>
                ) : (
                  <button
                    onClick={handleStopStreaming}
                    className="px-3 py-1 text-sm bg-red-600 text-white rounded hover:bg-red-700"
                  >
                    Stop Stream
                  </button>
                )}
              </>
            )}

            {/* Auto-scroll toggle */}
            <button
              onClick={() => setState(prev => ({ ...prev, autoScroll: !prev.autoScroll }))}
              className={`px-3 py-1 text-sm rounded border ${
                state.autoScroll
                  ? 'bg-blue-600 text-white border-blue-600'
                  : 'bg-gray-100 text-gray-700 border-gray-300 hover:bg-gray-200'
              }`}
            >
              Auto-scroll
            </button>
          </div>
        </div>

        {showSearch && (
          <div className="space-y-3">
            {/* Search input */}
            <div className="flex items-center space-x-2">
              <div className="flex-1 relative">
                <input
                  type="text"
                  value={state.searchQuery}
                  onChange={(e) => setState(prev => ({ ...prev, searchQuery: e.target.value }))}
                  onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
                  placeholder="Search logs..."
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
                <button
                  onClick={handleSearch}
                  disabled={state.isSearching}
                  className="absolute right-2 top-1/2 transform -translate-y-1/2 px-2 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
                >
                  {state.isSearching ? 'Searching...' : 'Search'}
                </button>
              </div>

              {/* Search options */}
              <div className="flex items-center space-x-2">
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={state.showRegexSearch}
                    onChange={(e) => setState(prev => ({ ...prev, showRegexSearch: e.target.checked }))}
                    className="mr-1"
                  />
                  <span className="text-sm text-gray-600">Regex</span>
                </label>
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={state.caseSensitive}
                    onChange={(e) => setState(prev => ({ ...prev, caseSensitive: e.target.checked }))}
                    className="mr-1"
                  />
                  <span className="text-sm text-gray-600">Case</span>
                </label>
              </div>
            </div>

            {/* Level filters */}
            <div className="flex items-center space-x-2">
              <span className="text-sm font-medium text-gray-700">Levels:</span>
              {Object.values(LogLevel).map(level => (
                <button
                  key={level}
                  onClick={() => toggleLevel(level)}
                  className={`px-2 py-1 text-xs rounded border ${
                    state.selectedLevels.has(level)
                      ? `${LEVEL_COLORS[level]} border-current bg-current bg-opacity-10`
                      : 'text-gray-400 border-gray-300 hover:bg-gray-100'
                  }`}
                >
                  {level}
                </button>
              ))}
            </div>

            {/* Context filters */}
            <div className="flex items-center space-x-2">
              <span className="text-sm font-medium text-gray-700">Contexts:</span>
              <div className="flex flex-wrap gap-1">
                {Object.values(LogEntryType).map(context => (
                  <button
                    key={context}
                    onClick={() => toggleContext(context)}
                    className={`px-2 py-1 text-xs rounded border ${
                      state.selectedContexts.has(context)
                        ? 'text-blue-600 border-blue-300 bg-blue-50'
                        : 'text-gray-400 border-gray-300 hover:bg-gray-100'
                    }`}
                  >
                    {context}
                  </button>
                ))}
              </div>
            </div>

            {/* Export controls */}
            {showExport && (
              <div className="flex items-center space-x-2">
                <span className="text-sm font-medium text-gray-700">Export:</span>
                <select
                  value={state.exportFormat}
                  onChange={(e) => setState(prev => ({ ...prev, exportFormat: e.target.value as LogExportFormat }))}
                  className="px-2 py-1 text-sm border border-gray-300 rounded"
                >
                  <option value={LogExportFormat.JSON}>JSON</option>
                  <option value={LogExportFormat.CSV}>CSV</option>
                  <option value={LogExportFormat.TEXT}>Text</option>
                </select>
                <button
                  onClick={handleExport}
                  disabled={state.isExporting}
                  className="px-3 py-1 text-sm bg-gray-600 text-white rounded hover:bg-gray-700 disabled:opacity-50"
                >
                  {state.isExporting ? 'Exporting...' : 'Export'}
                </button>
              </div>
            )}
          </div>
        )}

        {/* Stats */}
        <div className="mt-3 text-sm text-gray-600">
          Showing {filteredLogs.length.toLocaleString()} of {state.logs.length.toLocaleString()} log entries
          {state.isStreaming && <span className="ml-2 text-green-600">• Live streaming</span>}
        </div>
      </div>

      {/* Log entries list */}
      <div className="flex-1">
        {filteredLogs.length === 0 ? (
          <div className="flex items-center justify-center h-64 text-gray-500">
            <div className="text-center">
              <p className="text-lg">No log entries found</p>
              <p className="text-sm mt-2">
                {state.isStreaming
                  ? 'Waiting for new log entries...'
                  : 'Try adjusting your filters or starting the stream'
                }
              </p>
            </div>
          </div>
        ) : (
          <List
            ref={listRef}
            height={height - 200} // Account for header height
            itemCount={filteredLogs.length}
            itemSize={60} // Base height per log entry
            width="100%"
          >
            {LogEntryRow}
          </List>
        )}
      </div>
    </div>
  );
};

export default LogViewer;
