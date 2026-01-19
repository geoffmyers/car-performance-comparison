"use client";

import { useState, useMemo } from "react";
import { Table, ColumnFiltersState } from "@tanstack/react-table";
import { CarData, ColumnConfig } from "@/types/car";
import { parseNumericValue } from "@/lib/utils";

interface FilterPanelProps {
  table: Table<CarData>;
  columnConfigs: ColumnConfig[];
  columnFilters: ColumnFiltersState;
  setColumnFilters: (filters: ColumnFiltersState) => void;
}

interface NumericFilter {
  min?: number;
  max?: number;
}

export default function FilterPanel({
  table,
  columnConfigs,
  columnFilters,
  setColumnFilters,
}: FilterPanelProps) {
  const [activeFilterColumn, setActiveFilterColumn] = useState<string | null>(null);

  const uniqueValues = useMemo(() => {
    const values: Record<string, Set<string>> = {};
    const data = table.getCoreRowModel().rows;

    columnConfigs.forEach((config) => {
      if (!config.isNumeric && config.id !== "model" && config.id !== "engine" && config.id !== "torque") {
        values[config.id] = new Set();
        data.forEach((row) => {
          const value = row.getValue(config.id) as string;
          if (value && value.trim()) {
            values[config.id].add(value);
          }
        });
      }
    });

    return values;
  }, [table, columnConfigs]);

  const numericRanges = useMemo(() => {
    const ranges: Record<string, { min: number; max: number }> = {};
    const data = table.getCoreRowModel().rows;

    columnConfigs.forEach((config) => {
      if (config.isNumeric) {
        let min = Infinity;
        let max = -Infinity;
        data.forEach((row) => {
          const value = parseNumericValue(row.getValue(config.id) as string);
          if (value !== null) {
            min = Math.min(min, value);
            max = Math.max(max, value);
          }
        });
        if (min !== Infinity && max !== -Infinity) {
          ranges[config.id] = { min, max };
        }
      }
    });

    return ranges;
  }, [table, columnConfigs]);

  const getColumnFilter = (columnId: string): string | NumericFilter | undefined => {
    const filter = columnFilters.find((f) => f.id === columnId);
    return filter?.value as string | NumericFilter | undefined;
  };

  const setFilter = (columnId: string, value: string | NumericFilter | undefined) => {
    if (value === undefined || value === "" || (typeof value === "object" && value.min === undefined && value.max === undefined)) {
      setColumnFilters(columnFilters.filter((f) => f.id !== columnId));
    } else {
      const existing = columnFilters.find((f) => f.id === columnId);
      if (existing) {
        setColumnFilters(
          columnFilters.map((f) => (f.id === columnId ? { ...f, value } : f))
        );
      } else {
        setColumnFilters([...columnFilters, { id: columnId, value }]);
      }
    }
  };

  const clearAllFilters = () => {
    setColumnFilters([]);
  };

  const filterableColumns = columnConfigs.filter(
    (config) =>
      config.id !== "sources" &&
      (config.isNumeric || uniqueValues[config.id]?.size > 0)
  );

  const activeFiltersCount = columnFilters.length;

  return (
    <div className="rounded-xl border border-zinc-200 bg-white p-4 shadow-sm dark:border-zinc-700 dark:bg-zinc-800">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="font-semibold text-zinc-900 dark:text-zinc-100">
          Filters
          {activeFiltersCount > 0 && (
            <span className="ml-2 rounded-full bg-blue-100 px-2 py-0.5 text-sm text-blue-700 dark:bg-blue-900/30 dark:text-blue-400">
              {activeFiltersCount} active
            </span>
          )}
        </h3>
        {activeFiltersCount > 0 && (
          <button
            onClick={clearAllFilters}
            className="rounded-lg bg-red-50 px-3 py-1.5 text-sm font-medium text-red-600 transition-colors hover:bg-red-100 dark:bg-red-900/20 dark:text-red-400 dark:hover:bg-red-900/30"
          >
            Clear All
          </button>
        )}
      </div>

      {/* Active Filters Display */}
      {activeFiltersCount > 0 && (
        <div className="mb-4 flex flex-wrap gap-2">
          {columnFilters.map((filter) => {
            const config = columnConfigs.find((c) => c.id === filter.id);
            const value = filter.value;
            let displayValue: string;

            if (typeof value === "object" && value !== null) {
              const numFilter = value as NumericFilter;
              if (numFilter.min !== undefined && numFilter.max !== undefined) {
                displayValue = `${numFilter.min} - ${numFilter.max}`;
              } else if (numFilter.min !== undefined) {
                displayValue = `>= ${numFilter.min}`;
              } else if (numFilter.max !== undefined) {
                displayValue = `<= ${numFilter.max}`;
              } else {
                displayValue = "any";
              }
            } else {
              displayValue = String(value);
            }

            return (
              <div
                key={filter.id}
                className="flex items-center gap-2 rounded-full bg-blue-50 px-3 py-1 text-sm dark:bg-blue-900/30"
              >
                <span className="font-medium text-blue-700 dark:text-blue-400">
                  {config?.header}:
                </span>
                <span className="text-blue-600 dark:text-blue-300">
                  {displayValue}
                </span>
                <button
                  onClick={() => setFilter(filter.id, undefined)}
                  className="ml-1 text-blue-400 hover:text-blue-600 dark:hover:text-blue-200"
                >
                  <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            );
          })}
        </div>
      )}

      {/* Filter Column Selector */}
      <div className="mb-4">
        <label className="mb-2 block text-sm font-medium text-zinc-700 dark:text-zinc-300">
          Add Filter
        </label>
        <select
          value={activeFilterColumn || ""}
          onChange={(e) => setActiveFilterColumn(e.target.value || null)}
          className="w-full max-w-xs rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20 dark:border-zinc-600 dark:bg-zinc-700 dark:text-white"
        >
          <option value="">Select a column...</option>
          {filterableColumns.map((config) => (
            <option key={config.id} value={config.id}>
              {config.header} ({config.category})
            </option>
          ))}
        </select>
      </div>

      {/* Active Filter Editor */}
      {activeFilterColumn && (
        <FilterEditor
          columnId={activeFilterColumn}
          config={columnConfigs.find((c) => c.id === activeFilterColumn)!}
          value={getColumnFilter(activeFilterColumn)}
          onChange={(value) => setFilter(activeFilterColumn, value)}
          uniqueValues={uniqueValues[activeFilterColumn]}
          numericRange={numericRanges[activeFilterColumn]}
        />
      )}

      {/* Quick Filters */}
      <div className="mt-4 border-t border-zinc-200 pt-4 dark:border-zinc-700">
        <h4 className="mb-3 text-sm font-medium text-zinc-700 dark:text-zinc-300">
          Quick Filters
        </h4>
        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => {
              setFilter("propulsion", "electric");
            }}
            className="rounded-full border border-zinc-200 px-3 py-1 text-sm text-zinc-600 transition-colors hover:border-blue-300 hover:bg-blue-50 hover:text-blue-700 dark:border-zinc-600 dark:text-zinc-400 dark:hover:border-blue-500 dark:hover:bg-blue-900/20 dark:hover:text-blue-400"
          >
            Electric Cars
          </button>
          <button
            onClick={() => {
              setFilter("0_60_mph_sec", { min: undefined, max: 3 });
            }}
            className="rounded-full border border-zinc-200 px-3 py-1 text-sm text-zinc-600 transition-colors hover:border-blue-300 hover:bg-blue-50 hover:text-blue-700 dark:border-zinc-600 dark:text-zinc-400 dark:hover:border-blue-500 dark:hover:bg-blue-900/20 dark:hover:text-blue-400"
          >
            0-60 under 3s
          </button>
          <button
            onClick={() => {
              setFilter("top_speed_mph", { min: 200, max: undefined });
            }}
            className="rounded-full border border-zinc-200 px-3 py-1 text-sm text-zinc-600 transition-colors hover:border-blue-300 hover:bg-blue-50 hover:text-blue-700 dark:border-zinc-600 dark:text-zinc-400 dark:hover:border-blue-500 dark:hover:bg-blue-900/20 dark:hover:text-blue-400"
          >
            200+ mph
          </button>
          <button
            onClick={() => {
              setFilter("power_hp", { min: 1000, max: undefined });
            }}
            className="rounded-full border border-zinc-200 px-3 py-1 text-sm text-zinc-600 transition-colors hover:border-blue-300 hover:bg-blue-50 hover:text-blue-700 dark:border-zinc-600 dark:text-zinc-400 dark:hover:border-blue-500 dark:hover:bg-blue-900/20 dark:hover:text-blue-400"
          >
            1000+ HP
          </button>
          <button
            onClick={() => {
              setFilter("nurburgring_lap_sec", { min: undefined, max: 420 });
            }}
            className="rounded-full border border-zinc-200 px-3 py-1 text-sm text-zinc-600 transition-colors hover:border-blue-300 hover:bg-blue-50 hover:text-blue-700 dark:border-zinc-600 dark:text-zinc-400 dark:hover:border-blue-500 dark:hover:bg-blue-900/20 dark:hover:text-blue-400"
          >
            Nurburgring under 7 min
          </button>
        </div>
      </div>
    </div>
  );
}

interface FilterEditorProps {
  columnId: string;
  config: ColumnConfig;
  value: string | NumericFilter | undefined;
  onChange: (value: string | NumericFilter | undefined) => void;
  uniqueValues?: Set<string>;
  numericRange?: { min: number; max: number };
}

function FilterEditor({
  columnId,
  config,
  value,
  onChange,
  uniqueValues,
  numericRange,
}: FilterEditorProps) {
  if (config.isNumeric && numericRange) {
    const numValue = (value as NumericFilter) || {};

    return (
      <div className="rounded-lg border border-zinc-200 bg-zinc-50 p-4 dark:border-zinc-700 dark:bg-zinc-800/50">
        <h4 className="mb-3 font-medium text-zinc-800 dark:text-zinc-200">
          {config.header}
          {config.unit && (
            <span className="ml-1 text-sm text-zinc-500 dark:text-zinc-400">
              ({config.unit})
            </span>
          )}
        </h4>
        <div className="flex items-center gap-4">
          <div className="flex-1">
            <label className="mb-1 block text-xs text-zinc-500 dark:text-zinc-400">
              Min ({numericRange.min.toFixed(1)})
            </label>
            <input
              type="number"
              value={numValue.min ?? ""}
              onChange={(e) =>
                onChange({
                  ...numValue,
                  min: e.target.value ? parseFloat(e.target.value) : undefined,
                })
              }
              placeholder={numericRange.min.toFixed(1)}
              className="w-full rounded-lg border border-zinc-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20 dark:border-zinc-600 dark:bg-zinc-700 dark:text-white"
            />
          </div>
          <span className="text-zinc-400">to</span>
          <div className="flex-1">
            <label className="mb-1 block text-xs text-zinc-500 dark:text-zinc-400">
              Max ({numericRange.max.toFixed(1)})
            </label>
            <input
              type="number"
              value={numValue.max ?? ""}
              onChange={(e) =>
                onChange({
                  ...numValue,
                  max: e.target.value ? parseFloat(e.target.value) : undefined,
                })
              }
              placeholder={numericRange.max.toFixed(1)}
              className="w-full rounded-lg border border-zinc-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20 dark:border-zinc-600 dark:bg-zinc-700 dark:text-white"
            />
          </div>
        </div>
      </div>
    );
  }

  if (uniqueValues && uniqueValues.size > 0) {
    const sortedValues = Array.from(uniqueValues).sort();

    return (
      <div className="rounded-lg border border-zinc-200 bg-zinc-50 p-4 dark:border-zinc-700 dark:bg-zinc-800/50">
        <h4 className="mb-3 font-medium text-zinc-800 dark:text-zinc-200">
          {config.header}
        </h4>
        <select
          value={(value as string) || ""}
          onChange={(e) => onChange(e.target.value || undefined)}
          className="w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20 dark:border-zinc-600 dark:bg-zinc-700 dark:text-white"
        >
          <option value="">Any</option>
          {sortedValues.map((val) => (
            <option key={val} value={val}>
              {val}
            </option>
          ))}
        </select>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-zinc-200 bg-zinc-50 p-4 dark:border-zinc-700 dark:bg-zinc-800/50">
      <h4 className="mb-3 font-medium text-zinc-800 dark:text-zinc-200">
        {config.header}
      </h4>
      <input
        type="text"
        value={(value as string) || ""}
        onChange={(e) => onChange(e.target.value || undefined)}
        placeholder={`Filter by ${config.header.toLowerCase()}...`}
        className="w-full rounded-lg border border-zinc-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20 dark:border-zinc-600 dark:bg-zinc-700 dark:text-white"
      />
    </div>
  );
}
