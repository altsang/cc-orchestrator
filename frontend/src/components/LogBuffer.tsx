// High-performance log buffer component with virtual scrolling and efficient rendering

import React, { useMemo, useRef, useCallback } from 'react';
import { FixedSizeList as List } from 'react-window';
import { LogEntry, LogLevel, LogEntryType } from '../types';

interface LogBufferProps {
  logs: LogEntry[];
  height: number;
  onLogClick?: (log: LogEntry) => void;
  highlightTerms?: string[];
  showTimestamps?: boolean;
  showContext?: boolean;
  showMetadata?: boolean;
}

interface LogRowProps {
  index: number;
  style: React.CSSProperties;
  data: {
    logs: LogEntry[];
    highlightTerms?: string[];
    showTimestamps: boolean;
    showContext: boolean;
    showMetadata: boolean;
    onLogClick?: (log: LogEntry) => void;
  };
}

const LEVEL_COLORS = {
  [LogLevel.DEBUG]: 'text-gray-500',
  [LogLevel.INFO]: 'text-blue-600',
  [LogLevel.WARNING]: 'text-yellow-600',
  [LogLevel.ERROR]: 'text-red-600',
  [LogLevel.CRITICAL]: 'text-red-800 font-bold',
};

const LEVEL_BG_COLORS = {
  [LogLevel.DEBUG]: 'bg-gray-50',
  [LogLevel.INFO]: 'bg-blue-50',
  [LogLevel.WARNING]: 'bg-yellow-50',
  [LogLevel.ERROR]: 'bg-red-50',
  [LogLevel.CRITICAL]: 'bg-red-100',
};

const CONTEXT_COLORS = {
  [LogEntryType.SYSTEM]: 'bg-gray-100 text-gray-700',
  [LogEntryType.INSTANCE]: 'bg-blue-100 text-blue-700',
  [LogEntryType.TASK]: 'bg-green-100 text-green-700',
  [LogEntryType.WORKTREE]: 'bg-purple-100 text-purple-700',
  [LogEntryType.WEB]: 'bg-indigo-100 text-indigo-700',
  [LogEntryType.CLI]: 'bg-yellow-100 text-yellow-700',
  [LogEntryType.TMUX]: 'bg-pink-100 text-pink-700',
  [LogEntryType.INTEGRATION]: 'bg-teal-100 text-teal-700',
  [LogEntryType.DATABASE]: 'bg-orange-100 text-orange-700',
  [LogEntryType.PROCESS]: 'bg-red-100 text-red-700',
};

// Memoized row component for better performance
const LogRow = React.memo<LogRowProps>(({ index, style, data }) => {
  const { logs, highlightTerms, showTimestamps, showContext, showMetadata, onLogClick } = data;
  const log = logs[index];

  if (!log) {
    return <div style={style} className="px-3 py-2 text-gray-400">Loading...</div>;
  }

  const timestamp = new Date(log.timestamp).toLocaleString();
  const levelColor = LEVEL_COLORS[log.level] || 'text-gray-600';
  const levelBg = LEVEL_BG_COLORS[log.level] || 'bg-gray-50';
  const contextColor = log.context ? CONTEXT_COLORS[log.context] : 'bg-gray-100 text-gray-600';

  // Highlight search terms in message
  const highlightMessage = useCallback((message: string, terms?: string[]) => {
    if (!terms || terms.length === 0) {
      return <span>{message}</span>;
    }

    let highlightedMessage = message;
    terms.forEach(term => {
      if (term.trim()) {
        const regex = new RegExp(`(${term.replace(/[.*+?^${}()|[\\]\\\\]/g, '\\\\$&')})`, 'gi');
        highlightedMessage = highlightedMessage.replace(regex, '<mark>$1</mark>');
      }
    });

    return <span dangerouslySetInnerHTML={{ __html: highlightedMessage }} />;
  }, []);

  const handleRowClick = useCallback(() => {
    onLogClick?.(log);
  }, [log, onLogClick]);

  return (
    <div
      style={style}
      className={`px-3 py-2 border-b border-gray-100 ${levelBg} hover:bg-opacity-80 cursor-pointer transition-colors duration-150`}
      onClick={handleRowClick}
      title={`${log.logger}: ${log.message}`}
    >
      <div className="flex items-start space-x-2 text-sm">
        {/* Timestamp */}
        {showTimestamps && (
          <span className="text-xs text-gray-500 shrink-0 w-32 font-mono">
            {timestamp}
          </span>
        )}

        {/* Log level */}
        <span className={`font-semibold shrink-0 w-16 ${levelColor} text-xs uppercase`}>
          {log.level}
        </span>

        {/* Logger name */}
        <span className="text-gray-600 shrink-0 w-24 truncate text-xs" title={log.logger}>
          {log.logger.split('.').pop() || log.logger}
        </span>

        {/* Log message */}
        <span className="flex-1 text-gray-900 break-words text-sm leading-tight">
          {highlightMessage(log.message, highlightTerms)}
        </span>

        {/* Context badge */}
        {showContext && log.context && (
          <span className={`text-xs shrink-0 px-1.5 py-0.5 rounded-full ${contextColor}`}>
            {log.context.toUpperCase()}
          </span>
        )}

        {/* Instance and Task IDs */}
        <div className="flex space-x-1 shrink-0">
          {log.instance_id && (
            <span className="text-xs text-blue-600 px-1.5 py-0.5 bg-blue-100 rounded-full">
              I:{log.instance_id.slice(-4)}
            </span>
          )}
          {log.task_id && (
            <span className="text-xs text-green-600 px-1.5 py-0.5 bg-green-100 rounded-full">
              T:{log.task_id.slice(-4)}
            </span>
          )}
        </div>
      </div>

      {/* Exception information */}
      {log.exception && (
        <div className="mt-2 p-2 bg-red-100 border border-red-200 rounded text-xs">
          <div className="font-semibold text-red-800">
            {log.exception.type}: {log.exception.message}
          </div>
          {log.exception.traceback && (
            <details className="mt-1">
              <summary className="text-red-700 cursor-pointer hover:text-red-800">
                Show traceback
              </summary>
              <pre className="mt-1 text-red-700 whitespace-pre-wrap text-xs overflow-x-auto">
                {Array.isArray(log.exception.traceback)
                  ? log.exception.traceback.join('')
                  : log.exception.traceback}
              </pre>
            </details>
          )}
        </div>
      )}

      {/* Metadata */}
      {showMetadata && log.metadata && Object.keys(log.metadata).length > 0 && (
        <details className="mt-1">
          <summary className="text-xs text-gray-500 cursor-pointer hover:text-gray-700">
            Show metadata ({Object.keys(log.metadata).length} items)
          </summary>
          <div className="mt-1 p-2 bg-gray-100 rounded text-xs">
            <pre className="whitespace-pre-wrap">
              {JSON.stringify(log.metadata, null, 2)}
            </pre>
          </div>
        </details>
      )}

      {/* Module and function info */}
      {(log.module || log.function || log.line) && (
        <div className="mt-1 text-xs text-gray-400 flex space-x-2">
          {log.module && <span>📁 {log.module}</span>}
          {log.function && <span>⚡ {log.function}()</span>}
          {log.line && <span>📍 line {log.line}</span>}
        </div>
      )}
    </div>
  );
});

LogRow.displayName = 'LogRow';

export const LogBuffer: React.FC<LogBufferProps> = ({
  logs,
  height,
  onLogClick,
  highlightTerms = [],
  showTimestamps = true,
  showContext = true,
  showMetadata = false,
}) => {
  const listRef = useRef<List>(null);

  // Memoize row data to prevent unnecessary re-renders
  const rowData = useMemo(() => ({
    logs,
    highlightTerms,
    showTimestamps,
    showContext,
    showMetadata,
    onLogClick,
  }), [logs, highlightTerms, showTimestamps, showContext, showMetadata, onLogClick]);

  // Calculate dynamic row height based on log content
  const getItemSize = useCallback((index: number) => {
    const log = logs[index];
    if (!log) return 60;

    let baseHeight = 50; // Base height for log entry

    // Add height for exception details
    if (log.exception) {
      baseHeight += 80;
    }

    // Add height for metadata
    if (showMetadata && log.metadata && Object.keys(log.metadata).length > 0) {
      baseHeight += 40;
    }

    // Add height for module/function info
    if (log.module || log.function || log.line) {
      baseHeight += 20;
    }

    // Add height for long messages (word wrap estimation)
    const messageLength = log.message.length;
    if (messageLength > 100) {
      const extraLines = Math.floor(messageLength / 100);
      baseHeight += extraLines * 20;
    }

    return Math.min(baseHeight, 300); // Cap maximum height
  }, [logs, showMetadata]);

  // Scroll to specific log entry
  const scrollToIndex = useCallback((index: number) => {
    listRef.current?.scrollToItem(index, 'center');
  }, []);

  // Scroll to bottom
  const scrollToBottom = useCallback(() => {
    if (logs.length > 0) {
      listRef.current?.scrollToItem(logs.length - 1, 'end');
    }
  }, [logs.length]);

  // Scroll to top
  const scrollToTop = useCallback(() => {
    listRef.current?.scrollToItem(0, 'start');
  }, []);

  // Empty state
  if (logs.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-gray-500 bg-gray-50">
        <div className="text-center">
          <div className="text-4xl mb-4">📝</div>
          <p className="text-lg font-medium">No log entries</p>
          <p className="text-sm mt-2">Log entries will appear here as they are received</p>
        </div>
      </div>
    );
  }

  return (
    <div className="relative h-full bg-white">
      <List
        ref={listRef}
        height={height}
        itemCount={logs.length}
        itemSize={getItemSize}
        itemData={rowData}
        overscanCount={10} // Render extra items for smooth scrolling
        className="scrollbar-thin scrollbar-thumb-gray-300 scrollbar-track-gray-100"
      >
        {LogRow}
      </List>

      {/* Scroll controls */}
      <div className="absolute bottom-4 right-4 flex flex-col space-y-2">
        <button
          onClick={scrollToTop}
          className="p-2 bg-gray-700 text-white rounded-full shadow-lg hover:bg-gray-800 transition-colors"
          title="Scroll to top"
        >
          ⬆️
        </button>
        <button
          onClick={scrollToBottom}
          className="p-2 bg-gray-700 text-white rounded-full shadow-lg hover:bg-gray-800 transition-colors"
          title="Scroll to bottom"
        >
          ⬇️
        </button>
      </div>

      {/* Performance info overlay (dev mode) */}
      {process.env.NODE_ENV === 'development' && (
        <div className="absolute top-2 right-2 text-xs text-gray-500 bg-white bg-opacity-75 px-2 py-1 rounded">
          {logs.length.toLocaleString()} entries
        </div>
      )}
    </div>
  );
};

// Export scroll methods for external control
export const createLogBufferRef = () => {
  const ref = useRef<{
    scrollToIndex: (index: number) => void;
    scrollToBottom: () => void;
    scrollToTop: () => void;
  }>(null);

  return ref;
};

export default LogBuffer;
