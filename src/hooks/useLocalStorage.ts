"use client";

import { useState, useEffect, useCallback, useRef } from "react";

/**
 * A hook that syncs state with localStorage for persistence across page reloads.
 * Falls back to the default value if localStorage is unavailable or the key doesn't exist.
 *
 * Important: To avoid hydration mismatches, this hook always initializes with the
 * default value during SSR and the first client render, then syncs with localStorage
 * after hydration completes.
 */
export function useLocalStorage<T>(
  key: string,
  defaultValue: T
): [T, (value: T | ((prev: T) => T)) => void] {
  // Always initialize with defaultValue to avoid hydration mismatch
  const [storedValue, setStoredValue] = useState<T>(defaultValue);
  const [isHydrated, setIsHydrated] = useState(false);

  // Track if we've done the initial localStorage read
  const initialReadDone = useRef(false);

  // Sync with localStorage after hydration (runs only on client, after first render)
  useEffect(() => {
    if (initialReadDone.current) return;
    initialReadDone.current = true;

    try {
      const item = window.localStorage.getItem(key);
      if (item) {
        const parsed = JSON.parse(item) as T;
        setStoredValue(parsed);
      }
    } catch (error) {
      console.warn(`Error reading localStorage key "${key}":`, error);
    }

    setIsHydrated(true);
  }, [key, defaultValue]);

  const setValue = useCallback(
    (value: T | ((prev: T) => T)) => {
      try {
        setStoredValue((prev) => {
          // Allow value to be a function for functional updates
          const valueToStore = value instanceof Function ? value(prev) : value;

          // Save to localStorage
          if (typeof window !== "undefined") {
            window.localStorage.setItem(key, JSON.stringify(valueToStore));
          }

          return valueToStore;
        });
      } catch (error) {
        console.warn(`Error setting localStorage key "${key}":`, error);
      }
    },
    [key]
  );

  return [storedValue, setValue];
}

/**
 * Storage keys used throughout the app
 */
export const STORAGE_KEYS = {
  COLUMN_VISIBILITY: "car-comparison:column-visibility",
  QUERY_PARAMS: "car-comparison:query-params",
  PAGE_SIZE: "car-comparison:page-size",
} as const;
