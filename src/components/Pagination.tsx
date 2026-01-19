"use client";

import type { PaginationInfo } from "@/hooks/useCarsApi";

interface PaginationProps {
  pagination: PaginationInfo;
  onPageChange: (page: number) => void;
  onPageSizeChange: (pageSize: number) => void;
}

export default function Pagination({
  pagination,
  onPageChange,
  onPageSizeChange,
}: PaginationProps) {
  const { page, pageSize, totalCount, totalPages } = pagination;

  const startRecord = (page - 1) * pageSize + 1;
  const endRecord = Math.min(page * pageSize, totalCount);

  const getPageNumbers = () => {
    const pages: (number | "...")[] = [];
    const maxVisible = 5;

    if (totalPages <= maxVisible + 2) {
      for (let i = 1; i <= totalPages; i++) {
        pages.push(i);
      }
    } else {
      pages.push(1);

      const start = Math.max(2, page - 1);
      const end = Math.min(totalPages - 1, page + 1);

      if (start > 2) {
        pages.push("...");
      }

      for (let i = start; i <= end; i++) {
        pages.push(i);
      }

      if (end < totalPages - 1) {
        pages.push("...");
      }

      pages.push(totalPages);
    }

    return pages;
  };

  return (
    <div className="flex flex-wrap items-center justify-between gap-4">
      <div className="flex items-center gap-4">
        <div className="text-sm text-zinc-600 dark:text-zinc-400">
          Showing {startRecord.toLocaleString()} - {endRecord.toLocaleString()} of{" "}
          {totalCount.toLocaleString()} cars
        </div>

        <div className="flex items-center gap-2">
          <label
            htmlFor="pageSize"
            className="text-sm text-zinc-600 dark:text-zinc-400"
          >
            Per page:
          </label>
          <select
            id="pageSize"
            value={pageSize}
            onChange={(e) => onPageSizeChange(Number(e.target.value))}
            className="rounded-md border border-zinc-300 bg-white px-2 py-1 text-sm dark:border-zinc-700 dark:bg-zinc-800 dark:text-white"
          >
            <option value={25}>25</option>
            <option value={50}>50</option>
            <option value={100}>100</option>
          </select>
        </div>
      </div>

      <div className="flex items-center gap-1">
        <button
          onClick={() => onPageChange(1)}
          disabled={page === 1}
          className="rounded-md border border-zinc-300 p-2 text-sm font-medium transition-colors hover:bg-zinc-50 disabled:cursor-not-allowed disabled:opacity-50 dark:border-zinc-700 dark:hover:bg-zinc-800"
          title="First page"
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
              d="M11 19l-7-7 7-7m8 14l-7-7 7-7"
            />
          </svg>
        </button>

        <button
          onClick={() => onPageChange(page - 1)}
          disabled={page === 1}
          className="rounded-md border border-zinc-300 p-2 text-sm font-medium transition-colors hover:bg-zinc-50 disabled:cursor-not-allowed disabled:opacity-50 dark:border-zinc-700 dark:hover:bg-zinc-800"
          title="Previous page"
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
              d="M15 19l-7-7 7-7"
            />
          </svg>
        </button>

        <div className="flex items-center gap-1 px-2">
          {getPageNumbers().map((pageNum, index) =>
            pageNum === "..." ? (
              <span
                key={`ellipsis-${index}`}
                className="px-2 text-zinc-400 dark:text-zinc-500"
              >
                ...
              </span>
            ) : (
              <button
                key={pageNum}
                onClick={() => onPageChange(pageNum)}
                className={`min-w-[36px] rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                  page === pageNum
                    ? "bg-blue-600 text-white"
                    : "border border-zinc-300 hover:bg-zinc-50 dark:border-zinc-700 dark:hover:bg-zinc-800"
                }`}
              >
                {pageNum}
              </button>
            )
          )}
        </div>

        <button
          onClick={() => onPageChange(page + 1)}
          disabled={page === totalPages}
          className="rounded-md border border-zinc-300 p-2 text-sm font-medium transition-colors hover:bg-zinc-50 disabled:cursor-not-allowed disabled:opacity-50 dark:border-zinc-700 dark:hover:bg-zinc-800"
          title="Next page"
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
              d="M9 5l7 7-7 7"
            />
          </svg>
        </button>

        <button
          onClick={() => onPageChange(totalPages)}
          disabled={page === totalPages}
          className="rounded-md border border-zinc-300 p-2 text-sm font-medium transition-colors hover:bg-zinc-50 disabled:cursor-not-allowed disabled:opacity-50 dark:border-zinc-700 dark:hover:bg-zinc-800"
          title="Last page"
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
              d="M13 5l7 7-7 7M5 5l7 7-7 7"
            />
          </svg>
        </button>
      </div>
    </div>
  );
}
