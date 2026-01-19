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
