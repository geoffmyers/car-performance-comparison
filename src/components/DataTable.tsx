"use client";

import { useState, useMemo, useEffect } from "react";
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  getFilteredRowModel,
  flexRender,
  SortingState,
  ColumnFiltersState,
  VisibilityState,
  ColumnDef,
  FilterFn,
} from "@tanstack/react-table";
import Papa from "papaparse";
import { CarData, columnConfigs, columnCategories } from "@/types/car";
import { formatValue, formatLapTime, parseNumericValue } from "@/lib/utils";
import ColumnVisibilityPanel from "./ColumnVisibilityPanel";
import FilterPanel from "./FilterPanel";
import ManufacturerLogo from "./ManufacturerLogo";

const globalFilterFn: FilterFn<CarData> = (row, columnId, filterValue) => {
  const search = filterValue.toLowerCase();
  const value = row.getValue(columnId);
  return String(value ?? "").toLowerCase().includes(search);
};

interface NumericFilter {
  min?: number;
  max?: number;
}

const columnFilterFn: FilterFn<CarData> = (row, columnId, filterValue) => {
  const value = row.getValue(columnId) as string;

  // Handle numeric range filters
  if (typeof filterValue === "object" && filterValue !== null) {
    const numFilter = filterValue as NumericFilter;
    const numValue = parseNumericValue(value);

    if (numValue === null) return false;

    if (numFilter.min !== undefined && numValue < numFilter.min) return false;
    if (numFilter.max !== undefined && numValue > numFilter.max) return false;

    return true;
  }

  // Handle text filters
  if (typeof filterValue === "string") {
    return String(value ?? "").toLowerCase().includes(filterValue.toLowerCase());
  }

  return true;
};

export default function DataTable() {
  const [data, setData] = useState<CarData[]>([]);
  const [loading, setLoading] = useState(true);
  const [sorting, setSorting] = useState<SortingState>([]);
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([]);
  const [globalFilter, setGlobalFilter] = useState("");
  const [columnVisibility, setColumnVisibility] = useState<VisibilityState>({
    sources: false,
    nurburgring_date: false,
    nurburgring_driver: false,
    top_gear_episode: false,
    "0_100_kmh_sec": false,
    "0_200_kmh_sec": false,
    top_speed_kmh: false,
    power_kw: false,
  });
  const [showColumnPanel, setShowColumnPanel] = useState(false);
  const [showFilterPanel, setShowFilterPanel] = useState(false);

  useEffect(() => {
    fetch("/data/car-performance-data.csv")
      .then((response) => response.text())
      .then((csvText) => {
        const result = Papa.parse<CarData>(csvText, {
          header: true,
          skipEmptyLines: true,
        });
        setData(result.data);
        setLoading(false);
      })
      .catch((error) => {
        console.error("Error loading CSV:", error);
        setLoading(false);
      });
  }, []);

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
        cell: ({ getValue, row }) => {
          const value = getValue() as string;
          if (config.id === "manufacturer") {
            return (
              <div className="flex items-center gap-2">
                <ManufacturerLogo manufacturer={value} size={24} />
                <span>{value}</span>
              </div>
            );
          }
          if (config.id === "nurburgring_lap_sec" || config.id === "top_gear_lap_sec") {
            return formatLapTime(value);
          }
          return formatValue(value);
        },
        sortingFn: config.isNumeric
          ? (rowA, rowB, columnId) => {
              const a = parseNumericValue(rowA.getValue(columnId) as string);
              const b = parseNumericValue(rowB.getValue(columnId) as string);
              if (a === null && b === null) return 0;
              if (a === null) return 1;
              if (b === null) return -1;
              return a - b;
            }
          : "alphanumeric",
        filterFn: columnFilterFn,
      })),
    []
  );

  const table = useReactTable({
    data,
    columns,
    state: {
      sorting,
      columnFilters,
      globalFilter,
      columnVisibility,
    },
    onSortingChange: setSorting,
    onColumnFiltersChange: setColumnFilters,
    onGlobalFilterChange: setGlobalFilter,
    onColumnVisibilityChange: setColumnVisibility,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    globalFilterFn,
  });

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="flex items-center gap-3">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-zinc-300 border-t-blue-600"></div>
          <span className="text-lg text-zinc-600 dark:text-zinc-400">
            Loading car data...
          </span>
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
            value={globalFilter}
            onChange={(e) => setGlobalFilter(e.target.value)}
            placeholder="Search all columns..."
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
          {globalFilter && (
            <button
              onClick={() => setGlobalFilter("")}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200"
            >
              <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
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
            <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" />
            </svg>
            Filters
            {columnFilters.length > 0 && (
              <span className="flex h-5 w-5 items-center justify-center rounded-full bg-blue-600 text-xs text-white">
                {columnFilters.length}
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
            <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 17V7m0 10a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h2a2 2 0 012 2m0 10a2 2 0 002 2h2a2 2 0 002-2M9 7a2 2 0 012-2h2a2 2 0 012 2m0 10V7" />
            </svg>
            Columns
            <span className="text-xs text-zinc-500 dark:text-zinc-400">
              ({visibleColumnsCount}/{totalColumnsCount})
            </span>
          </button>
        </div>

        {/* Results count */}
        <div className="text-sm text-zinc-500 dark:text-zinc-400">
          {table.getFilteredRowModel().rows.length} of {data.length} cars
        </div>
      </div>

      {/* Panels */}
      {showFilterPanel && (
        <FilterPanel
          table={table}
          columnConfigs={columnConfigs}
          columnFilters={columnFilters}
          setColumnFilters={setColumnFilters}
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
                <tr key={headerGroup.id} className="bg-zinc-50 dark:bg-zinc-800">
                  {headerGroup.headers.map((header) => (
                    <th
                      key={header.id}
                      className="whitespace-nowrap border-b border-zinc-200 px-4 py-3 text-left text-sm font-semibold text-zinc-900 dark:border-zinc-700 dark:text-zinc-100"
                    >
                      {header.isPlaceholder ? null : (
                        <button
                          className={`flex items-center gap-2 ${
                            header.column.getCanSort()
                              ? "cursor-pointer select-none hover:text-blue-600 dark:hover:text-blue-400"
                              : ""
                          }`}
                          onClick={header.column.getToggleSortingHandler()}
                        >
                          {flexRender(
                            header.column.columnDef.header,
                            header.getContext()
                          )}
                          {{
                            asc: (
                              <svg className="h-4 w-4 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
                              </svg>
                            ),
                            desc: (
                              <svg className="h-4 w-4 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                              </svg>
                            ),
                          }[header.column.getIsSorted() as string] ?? (
                            <svg className="h-4 w-4 text-zinc-300 dark:text-zinc-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16V4m0 0L3 8m4-4l4 4m6 0v12m0 0l4-4m-4 4l-4-4" />
                            </svg>
                          )}
                        </button>
                      )}
                    </th>
                  ))}
                </tr>
              ))}
            </thead>
            <tbody>
              {table.getRowModel().rows.length === 0 ? (
                <tr>
                  <td
                    colSpan={visibleColumnsCount}
                    className="px-4 py-12 text-center text-zinc-500 dark:text-zinc-400"
                  >
                    <div className="flex flex-col items-center gap-2">
                      <svg className="h-12 w-12 text-zinc-300 dark:text-zinc-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      <span>No cars match your filters</span>
                      <button
                        onClick={() => {
                          setGlobalFilter("");
                          setColumnFilters([]);
                        }}
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

      {/* Footer Stats */}
      <div className="flex items-center justify-between text-sm text-zinc-500 dark:text-zinc-400">
        <div>
          Showing {table.getRowModel().rows.length} of {data.length} cars
        </div>
        <div className="flex items-center gap-4">
          {sorting.length > 0 && (
            <div className="flex items-center gap-2">
              <span>Sorted by:</span>
              {sorting.map((sort) => {
                const config = columnConfigs.find((c) => c.id === sort.id);
                return (
                  <span key={sort.id} className="rounded bg-zinc-100 px-2 py-0.5 dark:bg-zinc-800">
                    {config?.header} ({sort.desc ? "desc" : "asc"})
                  </span>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
