"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import type { CarData } from "@/types/car";

export interface CarsQuery {
  page?: number;
  pageSize?: number;
  sortBy?: string;
  sortOrder?: "asc" | "desc";
  manufacturer?: string;
  country?: string;
  yearMin?: number;
  yearMax?: number;
  search?: string;
  source?: string;
  // New categorical filters
  bodyStyle?: string;
  propulsion?: string;
  engineType?: string;
  engineAspiration?: string;
  enginePlacement?: string;
  drivetrain?: string;
  // Threshold filters
  displacementMin?: number;
  powerMin?: number;
  torqueMin?: number;
  weightMax?: number;
  powerToWeightMax?: number;
  accel060Max?: number;
  quarterMileMax?: number;
  topSpeedMin?: number;
}

export interface PaginationInfo {
  page: number;
  pageSize: number;
  totalCount: number;
  totalPages: number;
}

export interface CarsApiResponse {
  data: CarData[];
  pagination: PaginationInfo;
}

// Filter option with count
export interface FilterOption {
  value: string;
  count: number;
}

// Threshold option with count
export interface ThresholdOption {
  label: string;
  value: number;
  count: number;
}

export interface MetaData {
  totalCount: number;
  manufacturers: FilterOption[];
  countries: FilterOption[];
  sources: FilterOption[];
  yearRange: { min: number; max: number };
  bodyStyles: FilterOption[];
  propulsions: FilterOption[];
  engineTypes: FilterOption[];
  engineAspirations: FilterOption[];
  enginePlacements: FilterOption[];
  drivetrains: FilterOption[];
  displacementThresholds: ThresholdOption[];
  powerThresholds: ThresholdOption[];
  torqueThresholds: ThresholdOption[];
  weightThresholds: ThresholdOption[];
  powerToWeightThresholds: ThresholdOption[];
  accel060Thresholds: ThresholdOption[];
  quarterMileThresholds: ThresholdOption[];
  topSpeedThresholds: ThresholdOption[];
}

export interface UseCarsApiResult {
  data: CarData[];
  pagination: PaginationInfo | null;
  loading: boolean;
  error: Error | null;
  refetch: () => void;
}

export interface UseMetaResult {
  meta: MetaData | null;
  loading: boolean;
  error: Error | null;
}

function buildQueryString(params: CarsQuery): string {
  const searchParams = new URLSearchParams();

  if (params.page) searchParams.set("page", String(params.page));
  if (params.pageSize) searchParams.set("pageSize", String(params.pageSize));
  if (params.sortBy) searchParams.set("sortBy", params.sortBy);
  if (params.sortOrder) searchParams.set("sortOrder", params.sortOrder);
  if (params.manufacturer) searchParams.set("manufacturer", params.manufacturer);
  if (params.country) searchParams.set("country", params.country);
  if (params.yearMin) searchParams.set("yearMin", String(params.yearMin));
  if (params.yearMax) searchParams.set("yearMax", String(params.yearMax));
  if (params.search) searchParams.set("search", params.search);
  if (params.source) searchParams.set("source", params.source);
  // New categorical filters
  if (params.bodyStyle) searchParams.set("bodyStyle", params.bodyStyle);
  if (params.propulsion) searchParams.set("propulsion", params.propulsion);
  if (params.engineType) searchParams.set("engineType", params.engineType);
  if (params.engineAspiration) searchParams.set("engineAspiration", params.engineAspiration);
  if (params.enginePlacement) searchParams.set("enginePlacement", params.enginePlacement);
  if (params.drivetrain) searchParams.set("drivetrain", params.drivetrain);
  // Threshold filters
  if (params.displacementMin) searchParams.set("displacementMin", String(params.displacementMin));
  if (params.powerMin) searchParams.set("powerMin", String(params.powerMin));
  if (params.torqueMin) searchParams.set("torqueMin", String(params.torqueMin));
  if (params.weightMax) searchParams.set("weightMax", String(params.weightMax));
  if (params.powerToWeightMax) searchParams.set("powerToWeightMax", String(params.powerToWeightMax));
  if (params.accel060Max) searchParams.set("accel060Max", String(params.accel060Max));
  if (params.quarterMileMax) searchParams.set("quarterMileMax", String(params.quarterMileMax));
  if (params.topSpeedMin) searchParams.set("topSpeedMin", String(params.topSpeedMin));

  return searchParams.toString();
}

export function useCarsApi(params: CarsQuery): UseCarsApiResult {
  const [data, setData] = useState<CarData[]>([]);
  const [pagination, setPagination] = useState<PaginationInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const fetchData = useCallback(async () => {
    // Abort previous request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    const controller = new AbortController();
    abortControllerRef.current = controller;

    setLoading(true);
    setError(null);

    try {
      const queryString = buildQueryString(params);
      const response = await fetch(`/api/cars?${queryString}`, {
        signal: controller.signal,
      });

      if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
      }

      const result: CarsApiResponse = await response.json();

      // Convert numeric values back to strings for compatibility with CarData type
      const formattedData = result.data.map((row) => {
        const formatted: Record<string, string> = {};
        for (const [key, value] of Object.entries(row)) {
          if (key === "id") continue; // Skip the id field
          formatted[key] = value === null || value === undefined ? "" : String(value);
        }
        return formatted as unknown as CarData;
      });

      setData(formattedData);
      setPagination(result.pagination);
    } catch (err) {
      if (err instanceof Error && err.name === "AbortError") {
        // Request was cancelled, ignore
        return;
      }
      setError(err instanceof Error ? err : new Error("Unknown error"));
    } finally {
      setLoading(false);
    }
  }, [params]);

  useEffect(() => {
    fetchData();

    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, [fetchData]);

  return { data, pagination, loading, error, refetch: fetchData };
}

export function useMeta(): UseMetaResult {
  const [meta, setMeta] = useState<MetaData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    async function fetchMeta() {
      try {
        const response = await fetch("/api/cars/meta");
        if (!response.ok) {
          throw new Error(`API error: ${response.status}`);
        }
        const data: MetaData = await response.json();
        setMeta(data);
      } catch (err) {
        setError(err instanceof Error ? err : new Error("Unknown error"));
      } finally {
        setLoading(false);
      }
    }

    fetchMeta();
  }, []);

  return { meta, loading, error };
}

// Percentile thresholds for conditional styling
export interface PercentileThresholds {
  [key: string]: { p10: number | null; p90: number | null };
}

export interface UsePercentilesResult {
  percentiles: PercentileThresholds | null;
  loading: boolean;
  error: Error | null;
}

export function usePercentiles(): UsePercentilesResult {
  const [percentiles, setPercentiles] = useState<PercentileThresholds | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    async function fetchPercentiles() {
      try {
        const response = await fetch("/api/cars/percentiles");
        if (!response.ok) {
          throw new Error(`API error: ${response.status}`);
        }
        const data: PercentileThresholds = await response.json();
        setPercentiles(data);
      } catch (err) {
        setError(err instanceof Error ? err : new Error("Unknown error"));
      } finally {
        setLoading(false);
      }
    }

    fetchPercentiles();
  }, []);

  return { percentiles, loading, error };
}

// Columns where lower values are better (green for low, red for high)
export const LOWER_IS_BETTER_COLUMNS = new Set([
  "0_60_mph_sec",
  "0_100_kmh_sec",
  "0_100_mph_sec",
  "0_200_kmh_sec",
  "quarter_mile_sec",
  "curb_weight_lb",
  "braking_70_0_ft",
  "braking_100_0_ft",
  "nurburgring_lap_sec",
  "top_gear_lap_sec",
  "lightning_lap_sec",
  "power_to_weight",
]);

// Columns where higher values are better (green for high, red for low)
export const HIGHER_IS_BETTER_COLUMNS = new Set([
  "top_speed_mph",
  "top_speed_kmh",
  "quarter_mile_speed_mph",
  "power_hp",
  "power_kw",
  "torque",
  "skidpad_g",
]);

/**
 * Determine the percentile status for a value
 * @returns "top10" if in top 10% (best), "bottom10" if in bottom 10% (worst), or null
 */
export function getPercentileStatus(
  columnId: string,
  value: number | null,
  percentiles: PercentileThresholds | null
): "top10" | "bottom10" | null {
  if (value === null || !percentiles) return null;

  const thresholds = percentiles[columnId];
  if (!thresholds || thresholds.p10 === null || thresholds.p90 === null) return null;

  const isLowerBetter = LOWER_IS_BETTER_COLUMNS.has(columnId);
  const isHigherBetter = HIGHER_IS_BETTER_COLUMNS.has(columnId);

  if (!isLowerBetter && !isHigherBetter) return null;

  if (isLowerBetter) {
    // Lower is better: top 10% = value <= p10 (best), bottom 10% = value >= p90 (worst)
    if (value <= thresholds.p10) return "top10";
    if (value >= thresholds.p90) return "bottom10";
  } else {
    // Higher is better: top 10% = value >= p90 (best), bottom 10% = value <= p10 (worst)
    if (value >= thresholds.p90) return "top10";
    if (value <= thresholds.p10) return "bottom10";
  }

  return null;
}
