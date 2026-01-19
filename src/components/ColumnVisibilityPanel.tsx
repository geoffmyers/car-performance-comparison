"use client";

import { Table } from "@tanstack/react-table";
import { CarData, ColumnConfig } from "@/types/car";

interface ColumnVisibilityPanelProps {
  table: Table<CarData>;
  columnConfigs: ColumnConfig[];
  columnCategories: readonly string[];
}

export default function ColumnVisibilityPanel({
  table,
  columnConfigs,
  columnCategories,
}: ColumnVisibilityPanelProps) {
  const toggleAllInCategory = (category: string, visible: boolean) => {
    const columnsInCategory = columnConfigs.filter((c) => c.category === category);
    columnsInCategory.forEach((config) => {
      table.getColumn(config.id)?.toggleVisibility(visible);
    });
  };

  const getCategoryVisibility = (category: string) => {
    const columnsInCategory = columnConfigs.filter((c) => c.category === category);
    const visibleCount = columnsInCategory.filter(
      (config) => table.getColumn(config.id)?.getIsVisible()
    ).length;
    if (visibleCount === 0) return "none";
    if (visibleCount === columnsInCategory.length) return "all";
    return "some";
  };

  const showAll = () => {
    table.getAllColumns().forEach((column) => column.toggleVisibility(true));
  };

  const hideAll = () => {
    table.getAllColumns().forEach((column, index) => {
      if (index === 0) {
        column.toggleVisibility(true);
      } else {
        column.toggleVisibility(false);
      }
    });
  };

  return (
    <div className="rounded-xl border border-zinc-200 bg-white p-4 shadow-sm dark:border-zinc-700 dark:bg-zinc-800">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="font-semibold text-zinc-900 dark:text-zinc-100">
          Column Visibility
        </h3>
        <div className="flex gap-2">
          <button
            onClick={showAll}
            className="rounded-lg bg-zinc-100 px-3 py-1.5 text-sm font-medium text-zinc-700 transition-colors hover:bg-zinc-200 dark:bg-zinc-700 dark:text-zinc-300 dark:hover:bg-zinc-600"
          >
            Show All
          </button>
          <button
            onClick={hideAll}
            className="rounded-lg bg-zinc-100 px-3 py-1.5 text-sm font-medium text-zinc-700 transition-colors hover:bg-zinc-200 dark:bg-zinc-700 dark:text-zinc-300 dark:hover:bg-zinc-600"
          >
            Hide All
          </button>
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {columnCategories.map((category) => {
          const columnsInCategory = columnConfigs.filter(
            (c) => c.category === category
          );
          const visibility = getCategoryVisibility(category);

          return (
            <div
              key={category}
              className="rounded-lg border border-zinc-100 bg-zinc-50 p-3 dark:border-zinc-700 dark:bg-zinc-800/50"
            >
              <div className="mb-2 flex items-center justify-between">
                <h4 className="font-medium text-zinc-800 dark:text-zinc-200">
                  {category}
                </h4>
                <button
                  onClick={() =>
                    toggleAllInCategory(category, visibility !== "all")
                  }
                  className={`flex h-5 w-5 items-center justify-center rounded border transition-colors ${
                    visibility === "all"
                      ? "border-blue-500 bg-blue-500 text-white"
                      : visibility === "some"
                      ? "border-blue-500 bg-blue-100 dark:bg-blue-900/30"
                      : "border-zinc-300 bg-white dark:border-zinc-600 dark:bg-zinc-700"
                  }`}
                >
                  {visibility === "all" && (
                    <svg className="h-3 w-3" fill="currentColor" viewBox="0 0 20 20">
                      <path
                        fillRule="evenodd"
                        d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                        clipRule="evenodd"
                      />
                    </svg>
                  )}
                  {visibility === "some" && (
                    <svg className="h-3 w-3 text-blue-500" fill="currentColor" viewBox="0 0 20 20">
                      <path
                        fillRule="evenodd"
                        d="M3 10a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1z"
                        clipRule="evenodd"
                      />
                    </svg>
                  )}
                </button>
              </div>
              <div className="space-y-1">
                {columnsInCategory.map((config) => {
                  const column = table.getColumn(config.id);
                  const isVisible = column?.getIsVisible() ?? true;

                  return (
                    <label
                      key={config.id}
                      className="flex cursor-pointer items-center gap-2 rounded px-2 py-1 text-sm transition-colors hover:bg-zinc-100 dark:hover:bg-zinc-700"
                    >
                      <input
                        type="checkbox"
                        checked={isVisible}
                        onChange={() => column?.toggleVisibility()}
                        className="h-4 w-4 rounded border-zinc-300 text-blue-500 focus:ring-blue-500 dark:border-zinc-600 dark:bg-zinc-700"
                      />
                      <span
                        className={
                          isVisible
                            ? "text-zinc-700 dark:text-zinc-300"
                            : "text-zinc-400 dark:text-zinc-500"
                        }
                      >
                        {config.header}
                      </span>
                    </label>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
