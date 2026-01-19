"use client";

import { useState, useMemo, useCallback } from "react";
import {
  useReactTable,
  getCoreRowModel,
  flexRender,
  VisibilityState,
  ColumnDef,
} from "@tanstack/react-table";
import { CarData, columnConfigs, columnCategories } from "@/types/car";
import { formatValue, formatLapTime } from "@/lib/utils";
import { useCarsApi, type CarsQuery } from "@/hooks/useCarsApi";
import ColumnVisibilityPanel from "./ColumnVisibilityPanel";
import ManufacturerLogo from "./ManufacturerLogo";
import CountryFlag from "./CountryFlag";
import Pagination from "./Pagination";
import ServerFilterPanel from "./ServerFilterPanel";

export default function DataTable() {
  const [queryParams, setQueryParams] = useState<CarsQuery>({
    page: 1,
    pageSize: 50,
    sortBy: "0_60_mph_sec",
    sortOrder: "asc",
  });

  const [columnVisibility, setColumnVisibility] = useState<VisibilityState>({
    propulsion: false,
    "0_100_kmh_sec": false,
    "0_100_mph_sec": false,
    "0_200_kmh_sec": false,
    top_speed_kmh: false,
    power_kw: false,
    nurburgring_lap_sec: false,
    nurburgring_date: false,
    nurburgring_driver: false,
    top_gear_lap_sec: false,
    top_gear_episode: false,
    sources: false,
  });
  const [showColumnPanel, setShowColumnPanel] = useState(false);
  const [showFilterPanel, setShowFilterPanel] = useState(false);

  const { data, pagination, loading, error } = useCarsApi(queryParams);

  const handlePageChange = useCallback((page: number) => {
    setQueryParams((prev) => ({ ...prev, page }));
  }, []);

  const handlePageSizeChange = useCallback((pageSize: number) => {
    setQueryParams((prev) => ({ ...prev, pageSize, page: 1 }));
  }, []);

  const handleSortChange = useCallback((columnId: string) => {
    setQueryParams((prev) => {
      if (prev.sortBy === columnId) {
        return {
          ...prev,
          sortOrder: prev.sortOrder === "asc" ? "desc" : "asc",
          page: 1,
        };
      }
      return {
        ...prev,
        sortBy: columnId,
        sortOrder: "asc",
        page: 1,
      };
    });
  }, []);

  const handleSearchChange = useCallback((search: string) => {
    setQueryParams((prev) => ({
      ...prev,
      search: search || undefined,
      page: 1,
    }));
  }, []);

  const handleFilterChange = useCallback((filters: Partial<CarsQuery>) => {
    setQueryParams((prev) => ({
      ...prev,
      ...filters,
      page: 1,
    }));
  }, []);

  const clearAllFilters = useCallback(() => {
    setQueryParams({
      page: 1,
      pageSize: queryParams.pageSize,
      sortBy: queryParams.sortBy,
      sortOrder: queryParams.sortOrder,
    });
  }, [queryParams.pageSize, queryParams.sortBy, queryParams.sortOrder]);

  const activeFilterCount = useMemo(() => {
    let count = 0;
    if (queryParams.manufacturer) count++;
    if (queryParams.country) count++;
    if (queryParams.yearMin) count++;
    if (queryParams.yearMax) count++;
    if (queryParams.search) count++;
    return count;
  }, [queryParams]);

  const columns = useMemo<ColumnDef<CarData>[]>(
    () =>
      columnConfigs.map((config) => ({
        id: config.id,
        accessorKey: config.id,
        header: () => (
          <div className="flex items-center gap-1">
            <span>{config.header}</span>
            {config.unit && (
              <span className="text-xs text-zinc-400 dark:text-zinc-500">
                ({config.unit})
              </span>
            )}
          </div>
        ),
        cell: ({ getValue }) => {
          const value = getValue() as string;
          if (config.id === "manufacturer") {
            return (
              <div className="flex items-center gap-2">
                <ManufacturerLogo manufacturer={value} size={24} />
                <span>{value}</span>
              </div>
            );
          }
          if (config.id === "country") {
            return <CountryFlag countryCode={value} showName size="md" />;
          }
          if (
            config.id === "nurburgring_lap_sec" ||
            config.id === "top_gear_lap_sec"
          ) {
            return formatLapTime(value);
          }
          return formatValue(value);
        },
      })),
    []
  );

  const table = useReactTable({
    data,
    columns,
    state: {
      columnVisibility,
    },
    onColumnVisibilityChange: setColumnVisibility,
    getCoreRowModel: getCoreRowModel(),
    manualPagination: true,
    manualSorting: true,
    manualFiltering: true,
  });

  if (error) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="text-center">
          <div className="text-red-600 dark:text-red-400">
            Error loading car data
          </div>
          <div className="mt-2 text-sm text-zinc-500">{error.message}</div>
        </div>
      </div>
    );
  }

  const visibleColumnsCount = table.getVisibleLeafColumns().length;
  const totalColumnsCount = columns.length;

  return (
    <div className="space-y-4">
      {/* Controls Bar */}
      <div className="flex flex-wrap items-center gap-4">
        {/* Global Search */}
        <div className="relative flex-1 min-w-[200px] max-w-md">
          <input
            type="text"
            value={queryParams.search || ""}
            onChange={(e) => handleSearchChange(e.target.value)}
            placeholder="Search manufacturer or model..."
            className="w-full rounded-lg border border-zinc-300 bg-white px-4 py-2 pl-10 text-sm shadow-sm transition-colors focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20 dark:border-zinc-700 dark:bg-zinc-800 dark:text-white dark:placeholder-zinc-400"
          />
          <svg
            className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
            />
          </svg>
          {queryParams.search && (
            <button
              onClick={() => handleSearchChange("")}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200"
            >
              <svg
                className="h-4 w-4"
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
          )}
        </div>

        {/* Toggle Buttons */}
        <div className="flex gap-2">
          <button
            onClick={() => setShowFilterPanel(!showFilterPanel)}
            className={`flex items-center gap-2 rounded-lg border px-4 py-2 text-sm font-medium transition-colors ${
              showFilterPanel
                ? "border-blue-500 bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400"
                : "border-zinc-300 bg-white text-zinc-700 hover:bg-zinc-50 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-300 dark:hover:bg-zinc-700"
            }`}
          >
            <svg
              className="h-4 w-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z"
              />
            </svg>
            Filters
            {activeFilterCount > 0 && (
              <span className="flex h-5 w-5 items-center justify-center rounded-full bg-blue-600 text-xs text-white">
                {activeFilterCount}
              </span>
            )}
          </button>

          <button
            onClick={() => setShowColumnPanel(!showColumnPanel)}
            className={`flex items-center gap-2 rounded-lg border px-4 py-2 text-sm font-medium transition-colors ${
              showColumnPanel
                ? "border-blue-500 bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400"
                : "border-zinc-300 bg-white text-zinc-700 hover:bg-zinc-50 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-300 dark:hover:bg-zinc-700"
            }`}
          >
            <svg
              className="h-4 w-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 17V7m0 10a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h2a2 2 0 012 2m0 10a2 2 0 002 2h2a2 2 0 002-2M9 7a2 2 0 012-2h2a2 2 0 012 2m0 10V7"
              />
            </svg>
            Columns
            <span className="text-xs text-zinc-500 dark:text-zinc-400">
              ({visibleColumnsCount}/{totalColumnsCount})
            </span>
          </button>
        </div>

        {/* Results count */}
        <div className="text-sm text-zinc-500 dark:text-zinc-400">
          {loading ? (
            "Loading..."
          ) : pagination ? (
            `${pagination.totalCount.toLocaleString()} cars`
          ) : (
            `${data.length} cars`
          )}
        </div>
      </div>

      {/* Panels */}
      {showFilterPanel && (
        <ServerFilterPanel
          queryParams={queryParams}
          onFilterChange={handleFilterChange}
          onClearAll={clearAllFilters}
        />
      )}

      {showColumnPanel && (
        <ColumnVisibilityPanel
          table={table}
          columnConfigs={columnConfigs}
          columnCategories={columnCategories}
        />
      )}

      {/* Table */}
      <div className="overflow-hidden rounded-xl border border-zinc-200 shadow-sm dark:border-zinc-700">
        <div className="overflow-x-auto">
          <table className="w-full border-collapse">
            <thead>
              {table.getHeaderGroups().map((headerGroup) => (
                <tr
                  key={headerGroup.id}
                  className="bg-zinc-50 dark:bg-zinc-800"
                >
                  {headerGroup.headers.map((header) => {
                    const isSorted = queryParams.sortBy === header.id;

                    return (
                      <th
                        key={header.id}
                        className="whitespace-nowrap border-b border-zinc-200 px-4 py-3 text-left text-sm font-semibold text-zinc-900 dark:border-zinc-700 dark:text-zinc-100"
                      >
                        {header.isPlaceholder ? null : (
                          <button
                            className="flex items-center gap-2 cursor-pointer select-none hover:text-blue-600 dark:hover:text-blue-400"
                            onClick={() => handleSortChange(header.id)}
                          >
                            {flexRender(
                              header.column.columnDef.header,
                              header.getContext()
                            )}
                            {isSorted ? (
                              queryParams.sortOrder === "asc" ? (
                                <svg
                                  className="h-4 w-4 text-blue-600"
                                  fill="none"
                                  stroke="currentColor"
                                  viewBox="0 0 24 24"
                                >
                                  <path
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                    strokeWidth={2}
                                    d="M5 15l7-7 7 7"
                                  />
                                </svg>
                              ) : (
                                <svg
                                  className="h-4 w-4 text-blue-600"
                                  fill="none"
                                  stroke="currentColor"
                                  viewBox="0 0 24 24"
                                >
                                  <path
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                    strokeWidth={2}
                                    d="M19 9l-7 7-7-7"
                                  />
                                </svg>
                              )
                            ) : (
                              <svg
                                className="h-4 w-4 text-zinc-300 dark:text-zinc-600"
                                fill="none"
                                stroke="currentColor"
                                viewBox="0 0 24 24"
                              >
                                <path
                                  strokeLinecap="round"
                                  strokeLinejoin="round"
                                  strokeWidth={2}
                                  d="M7 16V4m0 0L3 8m4-4l4 4m6 0v12m0 0l4-4m-4 4l-4-4"
                                />
                              </svg>
                            )}
                          </button>
                        )}
                      </th>
                    );
                  })}
                </tr>
              ))}
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td
                    colSpan={visibleColumnsCount}
                    className="px-4 py-12 text-center"
                  >
                    <div className="flex items-center justify-center gap-3">
                      <div className="h-8 w-8 animate-spin rounded-full border-4 border-zinc-300 border-t-blue-600"></div>
                      <span className="text-lg text-zinc-600 dark:text-zinc-400">
                        Loading car data...
                      </span>
                    </div>
                  </td>
                </tr>
              ) : table.getRowModel().rows.length === 0 ? (
                <tr>
                  <td
                    colSpan={visibleColumnsCount}
                    className="px-4 py-12 text-center text-zinc-500 dark:text-zinc-400"
                  >
                    <div className="flex flex-col items-center gap-2">
                      <svg
                        className="h-12 w-12 text-zinc-300 dark:text-zinc-600"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={1.5}
                          d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                        />
                      </svg>
                      <span>No cars match your filters</span>
                      <button
                        onClick={clearAllFilters}
                        className="text-blue-600 hover:underline dark:text-blue-400"
                      >
                        Clear all filters
                      </button>
                    </div>
                  </td>
                </tr>
              ) : (
                table.getRowModel().rows.map((row, index) => (
                  <tr
                    key={row.id}
                    className={`border-b border-zinc-100 transition-colors hover:bg-blue-50/50 dark:border-zinc-800 dark:hover:bg-blue-900/10 ${
                      index % 2 === 0
                        ? "bg-white dark:bg-zinc-900"
                        : "bg-zinc-50/50 dark:bg-zinc-800/30"
                    }`}
                  >
                    {row.getVisibleCells().map((cell) => (
                      <td
                        key={cell.id}
                        className="whitespace-nowrap px-4 py-3 text-sm text-zinc-700 dark:text-zinc-300"
                      >
                        {flexRender(
                          cell.column.columnDef.cell,
                          cell.getContext()
                        )}
                      </td>
                    ))}
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Pagination */}
      {pagination && !loading && (
        <Pagination
          pagination={pagination}
          onPageChange={handlePageChange}
          onPageSizeChange={handlePageSizeChange}
        />
      )}

      {/* Footer Stats */}
      <div className="flex items-center justify-between text-sm text-zinc-500 dark:text-zinc-400">
        <div>
          {queryParams.sortBy && (
            <div className="flex items-center gap-2">
              <span>Sorted by:</span>
              <span className="rounded bg-zinc-100 px-2 py-0.5 dark:bg-zinc-800">
                {columnConfigs.find((c) => c.id === queryParams.sortBy)?.header}{" "}
                ({queryParams.sortOrder})
              </span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
