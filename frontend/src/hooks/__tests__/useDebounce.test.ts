import { renderHook, act } from '@testing-library/react';
import { useDebounce, useDebouncedRefetchers } from '../useDebounce';

// Mock timers
jest.useFakeTimers();

describe('useDebounce', () => {
  beforeEach(() => {
    jest.clearAllTimers();
  });

  afterEach(() => {
    jest.runOnlyPendingTimers();
    jest.useRealTimers();
  });

  it('should debounce function calls', () => {
    const mockCallback = jest.fn();
    const { result } = renderHook(() => useDebounce(mockCallback, 1000));

    // Call the debounced function multiple times
    act(() => {
      result.current('arg1');
      result.current('arg2');
      result.current('arg3');
    });

    // Should not have called the original function yet
    expect(mockCallback).not.toHaveBeenCalled();

    // Fast forward time
    act(() => {
      jest.advanceTimersByTime(1000);
    });

    // Should have called the function only once with the last arguments
    expect(mockCallback).toHaveBeenCalledTimes(1);
    expect(mockCallback).toHaveBeenCalledWith('arg3');
  });

  it('should cancel previous timeouts when called again', () => {
    const mockCallback = jest.fn();
    const { result } = renderHook(() => useDebounce(mockCallback, 1000));

    act(() => {
      result.current('first');
    });

    // Advance time partially
    act(() => {
      jest.advanceTimersByTime(500);
    });

    // Call again before first timeout completes
    act(() => {
      result.current('second');
    });

    // Advance time to complete the second timeout
    act(() => {
      jest.advanceTimersByTime(1000);
    });

    // Should only call with the second argument
    expect(mockCallback).toHaveBeenCalledTimes(1);
    expect(mockCallback).toHaveBeenCalledWith('second');
  });

  it('should update when callback or delay changes', () => {
    const mockCallback1 = jest.fn();
    const mockCallback2 = jest.fn();
    
    const { result, rerender } = renderHook(
      ({ callback, delay }) => useDebounce(callback, delay),
      {
        initialProps: { callback: mockCallback1, delay: 1000 }
      }
    );

    act(() => {
      result.current('test');
    });

    // Update the callback
    rerender({ callback: mockCallback2, delay: 1000 });

    act(() => {
      jest.advanceTimersByTime(1000);
    });

    // Should call the new callback
    expect(mockCallback1).not.toHaveBeenCalled();
    expect(mockCallback2).toHaveBeenCalledWith('test');
  });
});

describe('useDebouncedRefetchers', () => {
  beforeEach(() => {
    jest.clearAllTimers();
  });

  afterEach(() => {
    jest.runOnlyPendingTimers();
    jest.useRealTimers();
  });

  it('should create debounced versions of all refetchers', () => {
    const mockRefetchers = {
      instances: jest.fn(),
      tasks: jest.fn(),
      health: jest.fn(),
      alerts: jest.fn(),
    };

    const { result } = renderHook(() => 
      useDebouncedRefetchers(mockRefetchers, 1000)
    );

    // Should return debounced functions for all refetchers
    expect(result.current).toHaveProperty('instances');
    expect(result.current).toHaveProperty('tasks');
    expect(result.current).toHaveProperty('health');
    expect(result.current).toHaveProperty('alerts');

    // All should be functions
    expect(typeof result.current.instances).toBe('function');
    expect(typeof result.current.tasks).toBe('function');
    expect(typeof result.current.health).toBe('function');
    expect(typeof result.current.alerts).toBe('function');
  });

  it('should debounce each refetcher independently', () => {
    const mockRefetchers = {
      instances: jest.fn(),
      tasks: jest.fn(),
      health: jest.fn(),
      alerts: jest.fn(),
    };

    const { result } = renderHook(() => 
      useDebouncedRefetchers(mockRefetchers, 1000)
    );

    // Call different refetchers
    act(() => {
      result.current.instances();
      result.current.tasks();
      result.current.health();
      result.current.alerts();
    });

    // None should be called yet
    expect(mockRefetchers.instances).not.toHaveBeenCalled();
    expect(mockRefetchers.tasks).not.toHaveBeenCalled();
    expect(mockRefetchers.health).not.toHaveBeenCalled();
    expect(mockRefetchers.alerts).not.toHaveBeenCalled();

    // Advance time
    act(() => {
      jest.advanceTimersByTime(1000);
    });

    // All should have been called once
    expect(mockRefetchers.instances).toHaveBeenCalledTimes(1);
    expect(mockRefetchers.tasks).toHaveBeenCalledTimes(1);
    expect(mockRefetchers.health).toHaveBeenCalledTimes(1);
    expect(mockRefetchers.alerts).toHaveBeenCalledTimes(1);
  });

  it('should use custom delay', () => {
    const mockRefetchers = {
      instances: jest.fn(),
      tasks: jest.fn(),
      health: jest.fn(),
      alerts: jest.fn(),
    };

    const { result } = renderHook(() => 
      useDebouncedRefetchers(mockRefetchers, 500)
    );

    act(() => {
      result.current.instances();
    });

    // Should not be called after 400ms
    act(() => {
      jest.advanceTimersByTime(400);
    });
    expect(mockRefetchers.instances).not.toHaveBeenCalled();

    // Should be called after 500ms
    act(() => {
      jest.advanceTimersByTime(100);
    });
    expect(mockRefetchers.instances).toHaveBeenCalledTimes(1);
  });
});