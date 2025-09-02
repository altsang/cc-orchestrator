// React hook for log search functionality with debouncing and caching

import { useState, useCallback, useEffect, useRef, useMemo } from 'react';
import {
  LogEntry,
  LogLevel,
  LogEntryType,
  LogSearchRequest,
  LogSearchResponse
} from '../types';
import { searchLogs } from '../services/api';
import logger from '../utils/logger';

interface UseLogSearchOptions {
  debounceMs?: number;
  maxCacheSize?: number;
  instanceId?: string;
  taskId?: string;
}

interface LogSearchState {
  query: string;
  selectedLevels: Set<LogLevel>;
  selectedContexts: Set<LogEntryType>;
  regexEnabled: boolean;
  caseSensitive: boolean;
  dateRange: {
    start?: Date;
    end?: Date;
  };
}

interface LogSearchResult {
  entries: LogEntry[];
  totalCount: number;
  hasMore: boolean;
  searchDurationMs: number;
  isLoading: boolean;
  error: string | null;
}

interface SearchCacheEntry {
  request: LogSearchRequest;
  response: LogSearchResponse;
  timestamp: number;
}

export function useLogSearch(options: UseLogSearchOptions = {}) {
  const {
    debounceMs = 300,
    maxCacheSize = 50,
    instanceId,
    taskId,
  } = options;

  // Search state
  const [searchState, setSearchState] = useState<LogSearchState>({
    query: '',
    selectedLevels: new Set(Object.values(LogLevel)),
    selectedContexts: new Set(Object.values(LogEntryType)),
    regexEnabled: false,
    caseSensitive: false,
    dateRange: {},
  });

  // Search results
  const [searchResult, setSearchResult] = useState<LogSearchResult>({
    entries: [],
    totalCount: 0,
    hasMore: false,
    searchDurationMs: 0,
    isLoading: false,
    error: null,
  });

  // Pagination state
  const [pagination, setPagination] = useState({
    limit: 1000,
    offset: 0,
  });

  // Cache and refs
  const searchCacheRef = useRef<Map<string, SearchCacheEntry>>(new Map());
  const debounceTimeoutRef = useRef<NodeJS.Timeout>();
  const abortControllerRef = useRef<AbortController>();

  // Generate cache key for search request
  const getCacheKey = useCallback((request: LogSearchRequest): string => {
    return JSON.stringify({
      query: request.query,
      level: Array.from(request.level || []).sort(),
      context: Array.from(request.context || []).sort(),
      instance_id: request.instance_id,
      task_id: request.task_id,
      start_time: request.start_time,
      end_time: request.end_time,
      regex_enabled: request.regex_enabled,
      case_sensitive: request.case_sensitive,
      limit: request.limit,
      offset: request.offset,
    });
  }, []);

  // Build search request from current state
  const buildSearchRequest = useCallback((): LogSearchRequest => {
    return {
      query: searchState.query.trim() || undefined,
      level: searchState.selectedLevels.size < Object.values(LogLevel).length
        ? Array.from(searchState.selectedLevels)
        : undefined,
      context: searchState.selectedContexts.size < Object.values(LogEntryType).length
        ? Array.from(searchState.selectedContexts)
        : undefined,
      instance_id: instanceId,
      task_id: taskId,
      start_time: searchState.dateRange.start?.toISOString(),
      end_time: searchState.dateRange.end?.toISOString(),
      regex_enabled: searchState.regexEnabled,
      case_sensitive: searchState.caseSensitive,
      limit: pagination.limit,
      offset: pagination.offset,
    };
  }, [searchState, instanceId, taskId, pagination]);\n\n  // Check cache for existing results\n  const getCachedResult = useCallback((request: LogSearchRequest): LogSearchResponse | null => {\n    const cacheKey = getCacheKey(request);\n    const cached = searchCacheRef.current.get(cacheKey);\n    \n    if (cached) {\n      // Check if cache entry is still valid (5 minutes)\n      const isValid = (Date.now() - cached.timestamp) < 5 * 60 * 1000;\n      if (isValid) {\n        return cached.response;\n      } else {\n        searchCacheRef.current.delete(cacheKey);\n      }\n    }\n    \n    return null;\n  }, [getCacheKey]);\n\n  // Add result to cache\n  const setCachedResult = useCallback((request: LogSearchRequest, response: LogSearchResponse) => {\n    const cacheKey = getCacheKey(request);\n    \n    // Manage cache size\n    if (searchCacheRef.current.size >= maxCacheSize) {\n      const oldestKey = Array.from(searchCacheRef.current.keys())[0];\n      searchCacheRef.current.delete(oldestKey);\n    }\n    \n    searchCacheRef.current.set(cacheKey, {\n      request,\n      response,\n      timestamp: Date.now(),\n    });\n  }, [getCacheKey, maxCacheSize]);\n\n  // Perform search with caching and error handling\n  const performSearch = useCallback(async (request: LogSearchRequest) => {\n    // Cancel previous request\n    if (abortControllerRef.current) {\n      abortControllerRef.current.abort();\n    }\n\n    // Check cache first\n    const cachedResult = getCachedResult(request);\n    if (cachedResult) {\n      setSearchResult({\n        entries: cachedResult.entries,\n        totalCount: cachedResult.total_count,\n        hasMore: cachedResult.has_more,\n        searchDurationMs: cachedResult.search_duration_ms,\n        isLoading: false,\n        error: null,\n      });\n      return;\n    }\n\n    // Perform new search\n    setSearchResult(prev => ({ ...prev, isLoading: true, error: null }));\n    \n    const abortController = new AbortController();\n    abortControllerRef.current = abortController;\n\n    try {\n      const response = await searchLogs(request);\n      \n      if (!abortController.signal.aborted) {\n        // Cache the result\n        setCachedResult(request, response);\n        \n        setSearchResult({\n          entries: response.entries,\n          totalCount: response.total_count,\n          hasMore: response.has_more,\n          searchDurationMs: response.search_duration_ms,\n          isLoading: false,\n          error: null,\n        });\n\n        logger.info('Log search completed', {\n          query: request.query,\n          totalResults: response.total_count,\n          searchDuration: response.search_duration_ms,\n          cached: false,\n        });\n      }\n    } catch (error) {\n      if (!abortController.signal.aborted) {\n        const errorMessage = error instanceof Error ? error.message : 'Search failed';\n        setSearchResult(prev => ({ \n          ...prev, \n          isLoading: false, \n          error: errorMessage,\n        }));\n        logger.error('Log search failed', error as Error);\n      }\n    }\n  }, [getCachedResult, setCachedResult]);\n\n  // Debounced search trigger\n  const triggerSearch = useCallback(() => {\n    if (debounceTimeoutRef.current) {\n      clearTimeout(debounceTimeoutRef.current);\n    }\n\n    debounceTimeoutRef.current = setTimeout(() => {\n      const request = buildSearchRequest();\n      performSearch(request);\n    }, debounceMs);\n  }, [buildSearchRequest, performSearch, debounceMs]);\n\n  // Search controls\n  const setQuery = useCallback((query: string) => {\n    setSearchState(prev => ({ ...prev, query }));\n  }, []);\n\n  const toggleLevel = useCallback((level: LogLevel) => {\n    setSearchState(prev => {\n      const newLevels = new Set(prev.selectedLevels);\n      if (newLevels.has(level)) {\n        newLevels.delete(level);\n      } else {\n        newLevels.add(level);\n      }\n      return { ...prev, selectedLevels: newLevels };\n    });\n  }, []);\n\n  const toggleContext = useCallback((context: LogEntryType) => {\n    setSearchState(prev => {\n      const newContexts = new Set(prev.selectedContexts);\n      if (newContexts.has(context)) {\n        newContexts.delete(context);\n      } else {\n        newContexts.add(context);\n      }\n      return { ...prev, selectedContexts: newContexts };\n    });\n  }, []);\n\n  const setRegexEnabled = useCallback((enabled: boolean) => {\n    setSearchState(prev => ({ ...prev, regexEnabled: enabled }));\n  }, []);\n\n  const setCaseSensitive = useCallback((sensitive: boolean) => {\n    setSearchState(prev => ({ ...prev, caseSensitive: sensitive }));\n  }, []);\n\n  const setDateRange = useCallback((start?: Date, end?: Date) => {\n    setSearchState(prev => ({ \n      ...prev, \n      dateRange: { start, end }\n    }));\n  }, []);\n\n  const clearFilters = useCallback(() => {\n    setSearchState({\n      query: '',\n      selectedLevels: new Set(Object.values(LogLevel)),\n      selectedContexts: new Set(Object.values(LogEntryType)),\n      regexEnabled: false,\n      caseSensitive: false,\n      dateRange: {},\n    });\n    setPagination({ limit: 1000, offset: 0 });\n  }, []);\n\n  const loadMore = useCallback(() => {\n    if (searchResult.hasMore && !searchResult.isLoading) {\n      setPagination(prev => ({ \n        ...prev, \n        offset: prev.offset + prev.limit \n      }));\n    }\n  }, [searchResult.hasMore, searchResult.isLoading]);\n\n  const resetPagination = useCallback(() => {\n    setPagination({ limit: 1000, offset: 0 });\n  }, []);\n\n  // Execute search immediately\n  const executeSearch = useCallback(() => {\n    if (debounceTimeoutRef.current) {\n      clearTimeout(debounceTimeoutRef.current);\n    }\n    const request = buildSearchRequest();\n    performSearch(request);\n  }, [buildSearchRequest, performSearch]);\n\n  // Auto-search when state changes\n  useEffect(() => {\n    triggerSearch();\n  }, [\n    searchState.query,\n    searchState.selectedLevels,\n    searchState.selectedContexts,\n    searchState.regexEnabled,\n    searchState.caseSensitive,\n    searchState.dateRange,\n    pagination.offset,\n    triggerSearch,\n  ]);\n\n  // Cleanup on unmount\n  useEffect(() => {\n    return () => {\n      if (debounceTimeoutRef.current) {\n        clearTimeout(debounceTimeoutRef.current);\n      }\n      if (abortControllerRef.current) {\n        abortControllerRef.current.abort();\n      }\n    };\n  }, []);\n\n  // Memoized search terms for highlighting\n  const searchTerms = useMemo(() => {\n    if (!searchState.query.trim()) return [];\n    \n    if (searchState.regexEnabled) {\n      try {\n        // For regex, return the full pattern\n        return [searchState.query];\n      } catch {\n        // Invalid regex, treat as literal\n        return searchState.query.split(/\\s+/).filter(term => term.trim());\n      }\n    } else {\n      // Split query into words for highlighting\n      return searchState.query.split(/\\s+/).filter(term => term.trim());\n    }\n  }, [searchState.query, searchState.regexEnabled]);\n\n  // Active filters count\n  const activeFiltersCount = useMemo(() => {\n    let count = 0;\n    if (searchState.query.trim()) count++;\n    if (searchState.selectedLevels.size < Object.values(LogLevel).length) count++;\n    if (searchState.selectedContexts.size < Object.values(LogEntryType).length) count++;\n    if (searchState.dateRange.start || searchState.dateRange.end) count++;\n    if (searchState.regexEnabled) count++;\n    if (searchState.caseSensitive) count++;\n    return count;\n  }, [searchState]);\n\n  return {\n    // Search state\n    searchState,\n    searchResult,\n    pagination,\n    searchTerms,\n    activeFiltersCount,\n\n    // Search controls\n    setQuery,\n    toggleLevel,\n    toggleContext,\n    setRegexEnabled,\n    setCaseSensitive,\n    setDateRange,\n    clearFilters,\n    executeSearch,\n\n    // Pagination\n    loadMore,\n    resetPagination,\n\n    // Cache management\n    clearCache: useCallback(() => {\n      searchCacheRef.current.clear();\n    }, []),\n    getCacheStats: useCallback(() => ({\n      size: searchCacheRef.current.size,\n      maxSize: maxCacheSize,\n    }), [maxCacheSize]),\n  };\n}\n\nexport default useLogSearch;
