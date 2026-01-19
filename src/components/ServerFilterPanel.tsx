"use client";

import { useMeta, type CarsQuery } from "@/hooks/useCarsApi";
import { countryNames, sourceNames } from "@/types/car";

interface ServerFilterPanelProps {
  queryParams: CarsQuery;
  onFilterChange: (filters: Partial<CarsQuery>) => void;
  onClearAll: () => void;
}

export default function ServerFilterPanel({
  queryParams,
  onFilterChange,
  onClearAll,
}: ServerFilterPanelProps) {
  const { meta, loading } = useMeta();

  const hasActiveFilters =
    queryParams.manufacturer ||
    queryParams.country ||
    queryParams.yearMin ||
    queryParams.yearMax ||
    queryParams.source;

  if (loading) {
    return (
      <div className="rounded-lg border border-zinc-200 bg-white p-4 dark:border-zinc-700 dark:bg-zinc-800">
        <div className="flex items-center gap-2 text-zinc-500">
          <div className="h-4 w-4 animate-spin rounded-full border-2 border-zinc-300 border-t-blue-600"></div>
          Loading filters...
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-zinc-200 bg-white p-4 dark:border-zinc-700 dark:bg-zinc-800">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">
          Filters
        </h3>
        {hasActiveFilters && (
          <button
            onClick={onClearAll}
            className="text-sm text-blue-600 hover:underline dark:text-blue-400"
          >
            Clear all
          </button>
        )}
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
        {/* Manufacturer Filter */}
        <div>
          <label className="block text-xs font-medium text-zinc-600 dark:text-zinc-400 mb-1">
            Manufacturer
          </label>
          <select
            value={queryParams.manufacturer || ""}
            onChange={(e) =>
              onFilterChange({ manufacturer: e.target.value || undefined })
            }
            className="w-full rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-900 dark:text-white"
          >
            <option value="">All manufacturers</option>
            {meta?.manufacturers.map((manufacturer) => (
              <option key={manufacturer} value={manufacturer}>
                {manufacturer}
              </option>
            ))}
          </select>
        </div>

        {/* Country Filter */}
        <div>
          <label className="block text-xs font-medium text-zinc-600 dark:text-zinc-400 mb-1">
            Country
          </label>
          <select
            value={queryParams.country || ""}
            onChange={(e) =>
              onFilterChange({ country: e.target.value || undefined })
            }
            className="w-full rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-900 dark:text-white"
          >
            <option value="">All countries</option>
            {meta?.countries.map((country) => (
              <option key={country} value={country}>
                {countryNames[country] || country}
              </option>
            ))}
          </select>
        </div>

        {/* Source Filter */}
        <div>
          <label className="block text-xs font-medium text-zinc-600 dark:text-zinc-400 mb-1">
            Source
          </label>
          <select
            value={queryParams.source || ""}
            onChange={(e) =>
              onFilterChange({ source: e.target.value || undefined })
            }
            className="w-full rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-900 dark:text-white"
          >
            <option value="">All sources</option>
            {meta?.sources.map((source) => (
              <option key={source} value={source}>
                {sourceNames[source] || source}
              </option>
            ))}
          </select>
        </div>

        {/* Year Min */}
        <div>
          <label className="block text-xs font-medium text-zinc-600 dark:text-zinc-400 mb-1">
            Year From
          </label>
          <input
            type="number"
            min={meta?.yearRange.min}
            max={meta?.yearRange.max}
            value={queryParams.yearMin || ""}
            onChange={(e) =>
              onFilterChange({
                yearMin: e.target.value ? Number(e.target.value) : undefined,
              })
            }
            placeholder={meta?.yearRange.min?.toString()}
            className="w-full rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-900 dark:text-white"
          />
        </div>

        {/* Year Max */}
        <div>
          <label className="block text-xs font-medium text-zinc-600 dark:text-zinc-400 mb-1">
            Year To
          </label>
          <input
            type="number"
            min={meta?.yearRange.min}
            max={meta?.yearRange.max}
            value={queryParams.yearMax || ""}
            onChange={(e) =>
              onFilterChange({
                yearMax: e.target.value ? Number(e.target.value) : undefined,
              })
            }
            placeholder={meta?.yearRange.max?.toString()}
            className="w-full rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-900 dark:text-white"
          />
        </div>
      </div>

      {/* Active Filters Summary */}
      {hasActiveFilters && (
        <div className="mt-4 flex flex-wrap gap-2">
          {queryParams.manufacturer && (
            <span className="inline-flex items-center gap-1 rounded-full bg-blue-100 px-3 py-1 text-xs font-medium text-blue-800 dark:bg-blue-900/50 dark:text-blue-300">
              {queryParams.manufacturer}
              <button
                onClick={() => onFilterChange({ manufacturer: undefined })}
                className="ml-1 hover:text-blue-600"
              >
                <svg
                  className="h-3 w-3"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M6 18L18 6M6 6l12 12"
                  />
                </svg>
              </button>
            </span>
          )}
          {queryParams.country && (
            <span className="inline-flex items-center gap-1 rounded-full bg-blue-100 px-3 py-1 text-xs font-medium text-blue-800 dark:bg-blue-900/50 dark:text-blue-300">
              {countryNames[queryParams.country] || queryParams.country}
              <button
                onClick={() => onFilterChange({ country: undefined })}
                className="ml-1 hover:text-blue-600"
              >
                <svg
                  className="h-3 w-3"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M6 18L18 6M6 6l12 12"
                  />
                </svg>
              </button>
            </span>
          )}
          {(queryParams.yearMin || queryParams.yearMax) && (
            <span className="inline-flex items-center gap-1 rounded-full bg-blue-100 px-3 py-1 text-xs font-medium text-blue-800 dark:bg-blue-900/50 dark:text-blue-300">
              {queryParams.yearMin || "..."} - {queryParams.yearMax || "..."}
              <button
                onClick={() =>
                  onFilterChange({ yearMin: undefined, yearMax: undefined })
                }
                className="ml-1 hover:text-blue-600"
              >
                <svg
                  className="h-3 w-3"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M6 18L18 6M6 6l12 12"
                  />
                </svg>
              </button>
            </span>
          )}
          {queryParams.source && (
            <span className="inline-flex items-center gap-1 rounded-full bg-blue-100 px-3 py-1 text-xs font-medium text-blue-800 dark:bg-blue-900/50 dark:text-blue-300">
              {sourceNames[queryParams.source] || queryParams.source}
              <button
                onClick={() => onFilterChange({ source: undefined })}
                className="ml-1 hover:text-blue-600"
              >
                <svg
                  className="h-3 w-3"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M6 18L18 6M6 6l12 12"
                  />
                </svg>
              </button>
            </span>
          )}
        </div>
      )}
    </div>
  );
}
