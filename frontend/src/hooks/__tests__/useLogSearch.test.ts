// Comprehensive tests for useLogSearch hook

import { renderHook, act, waitFor } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';
import { useLogSearch } from '../useLogSearch';
import { LogLevel, LogEntryType, LogEntry } from '../../types';
import * as apiService from '../../services/api';

// Mock dependencies
vi.mock('../../services/api');
vi.mock('../../utils/logger');

const mockSearchLogs = vi.mocked(apiService.searchLogs);

// Sample log entries for testing
const sampleLogs: LogEntry[] = [
  {
    id: 'log_1',
    timestamp: '2023-10-01T10:00:00Z',
    level: LogLevel.INFO,
    logger: 'test.logger',
    message: 'Test info message',
    metadata: {},
  },
  {
    id: 'log_2',
    timestamp: '2023-10-01T10:01:00Z',
    level: LogLevel.ERROR,
    logger: 'error.logger',
    message: 'Test error message',
    metadata: {},
  },
  {
    id: 'log_3',
    timestamp: '2023-10-01T10:02:00Z',
    level: LogLevel.DEBUG,
    logger: 'debug.logger',
    message: 'Debug message for testing',
    metadata: {},
  },
];

describe('useLogSearch Hook', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();

    // Default mock implementation
    mockSearchLogs.mockResolvedValue({
      entries: sampleLogs,
      total_count: 3,
      has_more: false,
      search_duration_ms: 50,
    });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  describe('Initialization', () => {
    it('initializes with default state', () => {
      const { result } = renderHook(() => useLogSearch());

      expect(result.current.searchState.query).toBe('');
      expect(result.current.searchState.selectedLevels).toEqual(new Set(Object.values(LogLevel)));
      expect(result.current.searchState.selectedContexts).toEqual(new Set(Object.values(LogEntryType)));
      expect(result.current.searchState.regexEnabled).toBe(false);
      expect(result.current.searchState.caseSensitive).toBe(false);
      expect(result.current.searchResult.isLoading).toBe(false);
      expect(result.current.searchResult.entries).toEqual([]);
    });

    it('accepts custom options', () => {
      const options = {
        debounceMs: 500,
        maxCacheSize: 100,
        instanceId: 'test_instance',
        taskId: 'test_task',
      };

      const { result } = renderHook(() => useLogSearch(options));

      expect(result.current.searchState).toBeDefined();
      // Options are used internally but don't directly affect initial state
    });
  });

  describe('Search Functionality', () => {
    it('performs search with debouncing', async () => {
      const { result } = renderHook(() => useLogSearch({ debounceMs: 300 }));

      act(() => {
        result.current.setQuery('test query');
      });

      // Search should not be triggered immediately
      expect(mockSearchLogs).not.toHaveBeenCalled();

      // Advance timers to trigger debounced search
      act(() => {
        vi.advanceTimersByTime(300);
      });

      await waitFor(() => {
        expect(mockSearchLogs).toHaveBeenCalledWith(expect.objectContaining({
          query: 'test query',
        }));
      });

      await waitFor(() => {
        expect(result.current.searchResult.entries).toEqual(sampleLogs);
        expect(result.current.searchResult.totalCount).toBe(3);
      });
    });

    it('executes search immediately when executeSearch is called', async () => {
      const { result } = renderHook(() => useLogSearch());

      act(() => {
        result.current.setQuery('immediate search');
        result.current.executeSearch();
      });

      await waitFor(() => {
        expect(mockSearchLogs).toHaveBeenCalledWith(expect.objectContaining({
          query: 'immediate search',
        }));
      });
    });

    it('cancels previous search when new search is triggered', async () => {
      const { result } = renderHook(() => useLogSearch({ debounceMs: 100 }));

      // Start first search
      act(() => {
        result.current.setQuery('first query');
      });

      act(() => {
        vi.advanceTimersByTime(50); // Don't complete debounce
      });

      // Start second search before first completes
      act(() => {
        result.current.setQuery('second query');
      });

      act(() => {
        vi.advanceTimersByTime(100); // Complete second search
      });

      await waitFor(() => {
        expect(mockSearchLogs).toHaveBeenCalledTimes(1);
        expect(mockSearchLogs).toHaveBeenCalledWith(expect.objectContaining({
          query: 'second query',
        }));
      });
    });
  });

  describe('Search State Management', () => {
    it('updates query state', () => {
      const { result } = renderHook(() => useLogSearch());

      act(() => {
        result.current.setQuery('new query');
      });

      expect(result.current.searchState.query).toBe('new query');
    });

    it('toggles log levels', () => {
      const { result } = renderHook(() => useLogSearch());

      act(() => {
        result.current.toggleLevel(LogLevel.INFO);
      });

      expect(result.current.searchState.selectedLevels.has(LogLevel.INFO)).toBe(false);
      expect(result.current.searchState.selectedLevels.has(LogLevel.ERROR)).toBe(true);

      act(() => {
        result.current.toggleLevel(LogLevel.INFO);
      });

      expect(result.current.searchState.selectedLevels.has(LogLevel.INFO)).toBe(true);
    });

    it('toggles context types', () => {
      const { result } = renderHook(() => useLogSearch());

      act(() => {
        result.current.toggleContext(LogEntryType.SYSTEM);
      });

      expect(result.current.searchState.selectedContexts.has(LogEntryType.SYSTEM)).toBe(false);
      expect(result.current.searchState.selectedContexts.has(LogEntryType.WEB)).toBe(true);

      act(() => {
        result.current.toggleContext(LogEntryType.SYSTEM);
      });

      expect(result.current.searchState.selectedContexts.has(LogEntryType.SYSTEM)).toBe(true);
    });

    it('sets regex enabled state', () => {
      const { result } = renderHook(() => useLogSearch());

      act(() => {
        result.current.setRegexEnabled(true);
      });

      expect(result.current.searchState.regexEnabled).toBe(true);

      act(() => {
        result.current.setRegexEnabled(false);
      });

      expect(result.current.searchState.regexEnabled).toBe(false);
    });

    it('sets case sensitive state', () => {
      const { result } = renderHook(() => useLogSearch());

      act(() => {
        result.current.setCaseSensitive(true);
      });

      expect(result.current.searchState.caseSensitive).toBe(true);

      act(() => {
        result.current.setCaseSensitive(false);
      });

      expect(result.current.searchState.caseSensitive).toBe(false);
    });

    it('sets date range', () => {
      const { result } = renderHook(() => useLogSearch());

      const startDate = new Date('2023-10-01T00:00:00Z');
      const endDate = new Date('2023-10-02T00:00:00Z');

      act(() => {
        result.current.setDateRange(startDate, endDate);
      });

      expect(result.current.searchState.dateRange.start).toEqual(startDate);
      expect(result.current.searchState.dateRange.end).toEqual(endDate);
    });

    it('clears all filters', () => {
      const { result } = renderHook(() => useLogSearch());

      // Set some filters first
      act(() => {
        result.current.setQuery('test');
        result.current.toggleLevel(LogLevel.INFO);
        result.current.toggleContext(LogEntryType.SYSTEM);
        result.current.setRegexEnabled(true);
        result.current.setCaseSensitive(true);
        result.current.setDateRange(new Date(), new Date());
      });

      act(() => {
        result.current.clearFilters();
      });

      expect(result.current.searchState.query).toBe('');
      expect(result.current.searchState.selectedLevels).toEqual(new Set(Object.values(LogLevel)));
      expect(result.current.searchState.selectedContexts).toEqual(new Set(Object.values(LogEntryType)));
      expect(result.current.searchState.regexEnabled).toBe(false);
      expect(result.current.searchState.caseSensitive).toBe(false);
      expect(result.current.searchState.dateRange).toEqual({});
    });
  });

  describe('Search Terms Generation', () => {
    it('generates search terms from query', () => {
      const { result } = renderHook(() => useLogSearch());

      act(() => {
        result.current.setQuery('hello world test');
      });

      expect(result.current.searchTerms).toEqual(['hello', 'world', 'test']);
    });

    it('handles regex search terms', () => {
      const { result } = renderHook(() => useLogSearch());

      act(() => {
        result.current.setQuery('test.*pattern');
        result.current.setRegexEnabled(true);
      });

      expect(result.current.searchTerms).toEqual(['test.*pattern']);
    });

    it('filters empty search terms', () => {
      const { result } = renderHook(() => useLogSearch());

      act(() => {
        result.current.setQuery('  hello   world  ');
      });

      expect(result.current.searchTerms).toEqual(['hello', 'world']);
    });
  });

  describe('Active Filters Count', () => {
    it('counts active filters correctly', () => {
      const { result } = renderHook(() => useLogSearch());

      expect(result.current.activeFiltersCount).toBe(0);

      act(() => {
        result.current.setQuery('test');
      });

      expect(result.current.activeFiltersCount).toBe(1);

      act(() => {
        result.current.toggleLevel(LogLevel.INFO);
      });

      expect(result.current.activeFiltersCount).toBe(2);

      act(() => {
        result.current.setRegexEnabled(true);
      });

      expect(result.current.activeFiltersCount).toBe(3);
    });
  });

  describe('Pagination', () => {
    it('loads more results', async () => {
      mockSearchLogs
        .mockResolvedValueOnce({
          entries: sampleLogs.slice(0, 2),
          total_count: 3,
          has_more: true,
          search_duration_ms: 50,
        })
        .mockResolvedValueOnce({
          entries: sampleLogs.slice(2),
          total_count: 3,
          has_more: false,
          search_duration_ms: 30,
        });

      const { result } = renderHook(() => useLogSearch());

      // Initial search
      act(() => {
        result.current.executeSearch();
      });

      await waitFor(() => {
        expect(result.current.searchResult.hasMore).toBe(true);
      });

      // Load more
      act(() => {
        result.current.loadMore();
      });

      await waitFor(() => {
        expect(mockSearchLogs).toHaveBeenCalledTimes(2);
        expect(mockSearchLogs).toHaveBeenLastCalledWith(expect.objectContaining({
          offset: 1000,
        }));
      });
    });

    it('does not load more when no more results available', () => {
      const { result } = renderHook(() => useLogSearch());

      // Set state where hasMore is false
      act(() => {
        result.current.loadMore();
      });

      expect(mockSearchLogs).not.toHaveBeenCalled();
    });

    it('resets pagination', () => {
      const { result } = renderHook(() => useLogSearch());

      // Change pagination
      act(() => {
        result.current.loadMore();
        result.current.resetPagination();
      });

      expect(result.current.pagination.offset).toBe(0);
    });
  });

  describe('Caching', () => {
    it('uses cached results for identical requests', async () => {
      const { result } = renderHook(() => useLogSearch());

      // First search
      act(() => {
        result.current.setQuery('cached query');
        result.current.executeSearch();
      });

      await waitFor(() => {
        expect(mockSearchLogs).toHaveBeenCalledTimes(1);
      });

      // Second identical search should use cache
      act(() => {
        result.current.executeSearch();
      });

      // Should not make additional API call
      expect(mockSearchLogs).toHaveBeenCalledTimes(1);
    });

    it('makes new request for different queries', async () => {
      const { result } = renderHook(() => useLogSearch());

      // First search
      act(() => {
        result.current.setQuery('first query');
        result.current.executeSearch();
      });

      await waitFor(() => {
        expect(mockSearchLogs).toHaveBeenCalledTimes(1);
      });

      // Second different search
      act(() => {
        result.current.setQuery('second query');
        result.current.executeSearch();
      });

      await waitFor(() => {
        expect(mockSearchLogs).toHaveBeenCalledTimes(2);
      });
    });

    it('clears cache when requested', async () => {
      const { result } = renderHook(() => useLogSearch());

      // Populate cache
      act(() => {
        result.current.setQuery('cached query');
        result.current.executeSearch();
      });

      await waitFor(() => {
        expect(mockSearchLogs).toHaveBeenCalledTimes(1);
      });

      // Clear cache
      act(() => {
        result.current.clearCache();
      });

      // Same query should make new request
      act(() => {
        result.current.executeSearch();
      });

      await waitFor(() => {
        expect(mockSearchLogs).toHaveBeenCalledTimes(2);
      });
    });

    it('provides cache statistics', () => {
      const { result } = renderHook(() => useLogSearch({ maxCacheSize: 50 }));

      const stats = result.current.getCacheStats();
      expect(stats).toEqual({
        size: 0,
        maxSize: 50,
      });
    });
  });

  describe('Error Handling', () => {
    it('handles search errors', async () => {
      const searchError = new Error('Search failed');
      mockSearchLogs.mockRejectedValue(searchError);

      const { result } = renderHook(() => useLogSearch());

      act(() => {
        result.current.executeSearch();
      });

      await waitFor(() => {
        expect(result.current.searchResult.isLoading).toBe(false);
        expect(result.current.searchResult.error).toBe('Search failed');
      });
    });

    it('sets loading state during search', async () => {
      let resolveSearch: (value: any) => void;
      const searchPromise = new Promise((resolve) => {
        resolveSearch = resolve;
      });
      mockSearchLogs.mockReturnValue(searchPromise);

      const { result } = renderHook(() => useLogSearch());

      act(() => {
        result.current.executeSearch();
      });

      expect(result.current.searchResult.isLoading).toBe(true);

      act(() => {
        resolveSearch({
          entries: sampleLogs,
          total_count: 3,
          has_more: false,
          search_duration_ms: 50,
        });
      });

      await waitFor(() => {
        expect(result.current.searchResult.isLoading).toBe(false);
      });
    });
  });

  describe('Instance and Task Filtering', () => {
    it('includes instance ID in search requests', async () => {
      const { result } = renderHook(() =>
        useLogSearch({ instanceId: 'test_instance_123' })
      );

      act(() => {
        result.current.executeSearch();
      });

      await waitFor(() => {
        expect(mockSearchLogs).toHaveBeenCalledWith(expect.objectContaining({
          instance_id: 'test_instance_123',
        }));
      });
    });

    it('includes task ID in search requests', async () => {
      const { result } = renderHook(() =>
        useLogSearch({ taskId: 'test_task_456' })
      );

      act(() => {
        result.current.executeSearch();
      });

      await waitFor(() => {
        expect(mockSearchLogs).toHaveBeenCalledWith(expect.objectContaining({
          task_id: 'test_task_456',
        }));
      });
    });
  });

  describe('Auto-search Behavior', () => {
    it('automatically searches when state changes', async () => {
      const { result } = renderHook(() => useLogSearch({ debounceMs: 100 }));

      act(() => {
        result.current.setQuery('auto search');
      });

      act(() => {
        vi.advanceTimersByTime(100);
      });

      await waitFor(() => {
        expect(mockSearchLogs).toHaveBeenCalledWith(expect.objectContaining({
          query: 'auto search',
        }));
      });
    });

    it('auto-searches when filters change', async () => {
      const { result } = renderHook(() => useLogSearch({ debounceMs: 100 }));

      act(() => {
        result.current.toggleLevel(LogLevel.ERROR);
      });

      act(() => {
        vi.advanceTimersByTime(100);
      });

      await waitFor(() => {
        expect(mockSearchLogs).toHaveBeenCalledWith(expect.objectContaining({
          level: expect.not.arrayContaining([LogLevel.ERROR]),
        }));
      });
    });
  });

  describe('Cleanup', () => {
    it('cleans up timers and requests on unmount', () => {
      const { unmount } = renderHook(() => useLogSearch());

      // Start a search
      act(() => {
        unmount();
      });

      // No errors should occur during cleanup
      expect(true).toBe(true);
    });
  });
});
