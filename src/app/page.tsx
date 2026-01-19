"use client";

import { useMeta } from "@/hooks/useCarsApi";
import DataTable from "@/components/DataTable";

export default function Home() {
  const { meta, loading: metaLoading } = useMeta();

  // Format sources for display (comma-separated list)
  const sourcesList = meta?.sources.map((s) => s.value).join(", ") || "Wikipedia";

  // Format vehicle count with commas
  const vehicleCount = meta?.totalCount?.toLocaleString() || "50,000+";

  return (
    <div className="min-h-screen bg-gradient-to-b from-zinc-50 to-zinc-100 dark:from-zinc-900 dark:to-zinc-950">
      {/* Header */}
      <header className="border-b border-zinc-200 bg-white/80 backdrop-blur-sm dark:border-zinc-800 dark:bg-zinc-900/80">
        <div className="mx-auto max-w-[1800px] px-4 py-6 sm:px-6 lg:px-8">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-zinc-900 dark:text-white sm:text-3xl">
              Car Performance Database
            </h1>
            <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">
              Compare acceleration, top speed, power, and lap times across{" "}
              <span className={metaLoading ? "animate-pulse" : ""}>
                {vehicleCount}
              </span>{" "}
              vehicles
            </p>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="mx-auto max-w-[1800px] px-4 py-6 sm:px-6 lg:px-8">
        <DataTable />
      </main>

      {/* Footer */}
      <footer className="border-t border-zinc-200 bg-white/50 dark:border-zinc-800 dark:bg-zinc-900/50">
        <div className="mx-auto max-w-[1800px] px-4 py-4 sm:px-6 lg:px-8">
          <p className="text-center text-sm text-zinc-500 dark:text-zinc-400">
            Data sourced from {sourcesList}. Built with Next.js and TanStack Table.
          </p>
        </div>
      </footer>
    </div>
  );
}
