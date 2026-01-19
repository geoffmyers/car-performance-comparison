"use client";

import { useMeta, type CarsQuery, type FilterOption, type ThresholdOption } from "@/hooks/useCarsApi";
import { countryNames } from "@/types/car";

interface ServerFilterPanelProps {
  queryParams: CarsQuery;
  onFilterChange: (filters: Partial<CarsQuery>) => void;
  onClearAll: () => void;
}

// Reusable close button SVG
function CloseIcon() {
  return (
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
  );
}

// Filter tag component
function FilterTag({
  label,
  onRemove,
}: {
  label: string;
  onRemove: () => void;
}) {
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-blue-100 px-3 py-1 text-xs font-medium text-blue-800 dark:bg-blue-900/50 dark:text-blue-300">
      {label}
      <button onClick={onRemove} className="ml-1 hover:text-blue-600">
        <CloseIcon />
      </button>
    </span>
  );
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
    queryParams.source ||
    queryParams.bodyStyle ||
    queryParams.propulsion ||
    queryParams.engineType ||
    queryParams.engineAspiration ||
    queryParams.enginePlacement ||
    queryParams.drivetrain ||
    queryParams.displacementMin ||
    queryParams.powerMin ||
    queryParams.torqueMin ||
    queryParams.weightMax ||
    queryParams.powerToWeightMax ||
    queryParams.accel060Max ||
    queryParams.quarterMileMax ||
    queryParams.topSpeedMin;

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

  // Helper to render a categorical filter select
  const renderCategoricalSelect = (
    label: string,
    paramKey: keyof CarsQuery,
    options: FilterOption[] | undefined,
    placeholder: string,
    displayTransform?: (value: string) => string
  ) => (
    <div>
      <label className="block text-xs font-medium text-zinc-600 dark:text-zinc-400 mb-1">
        {label}
      </label>
      <select
        value={(queryParams[paramKey] as string) || ""}
        onChange={(e) =>
          onFilterChange({ [paramKey]: e.target.value || undefined })
        }
        className="w-full rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-900 dark:text-white"
      >
        <option value="">{placeholder}</option>
        {options?.map((option) => (
          <option key={option.value} value={option.value}>
            {displayTransform ? displayTransform(option.value) : option.value} ({option.count})
          </option>
        ))}
      </select>
    </div>
  );

  // Helper to render a threshold filter select
  const renderThresholdSelect = (
    label: string,
    paramKey: keyof CarsQuery,
    options: ThresholdOption[] | undefined,
    placeholder: string
  ) => (
    <div>
      <label className="block text-xs font-medium text-zinc-600 dark:text-zinc-400 mb-1">
        {label}
      </label>
      <select
        value={(queryParams[paramKey] as number) || ""}
        onChange={(e) =>
          onFilterChange({
            [paramKey]: e.target.value ? Number(e.target.value) : undefined,
          })
        }
        className="w-full rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-900 dark:text-white"
      >
        <option value="">{placeholder}</option>
        {options?.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label} ({option.count})
          </option>
        ))}
      </select>
    </div>
  );

  // Find the display label for a threshold value
  const findThresholdLabel = (
    options: ThresholdOption[] | undefined,
    value: number | undefined
  ): string | null => {
    if (!value || !options) return null;
    const option = options.find((o) => o.value === value);
    return option?.label || null;
  };

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

      {/* Basic Filters Row */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5 mb-4">
        {renderCategoricalSelect(
          "Manufacturer",
          "manufacturer",
          meta?.manufacturers,
          "All manufacturers"
        )}
        {renderCategoricalSelect(
          "Country",
          "country",
          meta?.countries,
          "All countries",
          (value) => countryNames[value] || value
        )}
        {renderCategoricalSelect(
          "Source",
          "source",
          meta?.sources,
          "All sources"
        )}

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

      {/* Vehicle Characteristics Filters */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6 mb-4">
        {renderCategoricalSelect(
          "Body Style",
          "bodyStyle",
          meta?.bodyStyles,
          "All body styles"
        )}
        {renderCategoricalSelect(
          "Powertrain",
          "propulsion",
          meta?.propulsions,
          "All powertrains"
        )}
        {renderCategoricalSelect(
          "Engine Type",
          "engineType",
          meta?.engineTypes,
          "All engine types"
        )}
        {renderCategoricalSelect(
          "Aspiration",
          "engineAspiration",
          meta?.engineAspirations,
          "All aspirations"
        )}
        {renderCategoricalSelect(
          "Engine Position",
          "enginePlacement",
          meta?.enginePlacements,
          "All positions"
        )}
        {renderCategoricalSelect(
          "Drivetrain",
          "drivetrain",
          meta?.drivetrains,
          "All drivetrains"
        )}
      </div>

      {/* Performance Threshold Filters */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4 lg:grid-cols-8">
        {renderThresholdSelect(
          "Displacement",
          "displacementMin",
          meta?.displacementThresholds,
          "Any displacement"
        )}
        {renderThresholdSelect(
          "Power",
          "powerMin",
          meta?.powerThresholds,
          "Any power"
        )}
        {renderThresholdSelect(
          "Torque",
          "torqueMin",
          meta?.torqueThresholds,
          "Any torque"
        )}
        {renderThresholdSelect(
          "Weight",
          "weightMax",
          meta?.weightThresholds,
          "Any weight"
        )}
        {renderThresholdSelect(
          "Power/Weight",
          "powerToWeightMax",
          meta?.powerToWeightThresholds,
          "Any ratio"
        )}
        {renderThresholdSelect(
          "0-60 mph",
          "accel060Max",
          meta?.accel060Thresholds,
          "Any time"
        )}
        {renderThresholdSelect(
          "Quarter Mile",
          "quarterMileMax",
          meta?.quarterMileThresholds,
          "Any time"
        )}
        {renderThresholdSelect(
          "Top Speed",
          "topSpeedMin",
          meta?.topSpeedThresholds,
          "Any speed"
        )}
      </div>

      {/* Active Filters Summary */}
      {hasActiveFilters && (
        <div className="mt-4 flex flex-wrap gap-2">
          {queryParams.manufacturer && (
            <FilterTag
              label={queryParams.manufacturer}
              onRemove={() => onFilterChange({ manufacturer: undefined })}
            />
          )}
          {queryParams.country && (
            <FilterTag
              label={countryNames[queryParams.country] || queryParams.country}
              onRemove={() => onFilterChange({ country: undefined })}
            />
          )}
          {(queryParams.yearMin || queryParams.yearMax) && (
            <FilterTag
              label={`${queryParams.yearMin || "..."} - ${queryParams.yearMax || "..."}`}
              onRemove={() =>
                onFilterChange({ yearMin: undefined, yearMax: undefined })
              }
            />
          )}
          {queryParams.source && (
            <FilterTag
              label={queryParams.source}
              onRemove={() => onFilterChange({ source: undefined })}
            />
          )}
          {queryParams.bodyStyle && (
            <FilterTag
              label={`Body: ${queryParams.bodyStyle}`}
              onRemove={() => onFilterChange({ bodyStyle: undefined })}
            />
          )}
          {queryParams.propulsion && (
            <FilterTag
              label={`Powertrain: ${queryParams.propulsion}`}
              onRemove={() => onFilterChange({ propulsion: undefined })}
            />
          )}
          {queryParams.engineType && (
            <FilterTag
              label={`Engine: ${queryParams.engineType}`}
              onRemove={() => onFilterChange({ engineType: undefined })}
            />
          )}
          {queryParams.engineAspiration && (
            <FilterTag
              label={`Aspiration: ${queryParams.engineAspiration}`}
              onRemove={() => onFilterChange({ engineAspiration: undefined })}
            />
          )}
          {queryParams.enginePlacement && (
            <FilterTag
              label={`Position: ${queryParams.enginePlacement}`}
              onRemove={() => onFilterChange({ enginePlacement: undefined })}
            />
          )}
          {queryParams.drivetrain && (
            <FilterTag
              label={`Drive: ${queryParams.drivetrain}`}
              onRemove={() => onFilterChange({ drivetrain: undefined })}
            />
          )}
          {queryParams.displacementMin && (
            <FilterTag
              label={findThresholdLabel(meta?.displacementThresholds, queryParams.displacementMin) || `≥${queryParams.displacementMin}L`}
              onRemove={() => onFilterChange({ displacementMin: undefined })}
            />
          )}
          {queryParams.powerMin && (
            <FilterTag
              label={findThresholdLabel(meta?.powerThresholds, queryParams.powerMin) || `≥${queryParams.powerMin} hp`}
              onRemove={() => onFilterChange({ powerMin: undefined })}
            />
          )}
          {queryParams.torqueMin && (
            <FilterTag
              label={findThresholdLabel(meta?.torqueThresholds, queryParams.torqueMin) || `≥${queryParams.torqueMin} lb-ft`}
              onRemove={() => onFilterChange({ torqueMin: undefined })}
            />
          )}
          {queryParams.weightMax && (
            <FilterTag
              label={findThresholdLabel(meta?.weightThresholds, queryParams.weightMax) || `≤${queryParams.weightMax} lbs`}
              onRemove={() => onFilterChange({ weightMax: undefined })}
            />
          )}
          {queryParams.powerToWeightMax && (
            <FilterTag
              label={findThresholdLabel(meta?.powerToWeightThresholds, queryParams.powerToWeightMax) || `≤${queryParams.powerToWeightMax} lb/hp`}
              onRemove={() => onFilterChange({ powerToWeightMax: undefined })}
            />
          )}
          {queryParams.accel060Max && (
            <FilterTag
              label={findThresholdLabel(meta?.accel060Thresholds, queryParams.accel060Max) || `≤${queryParams.accel060Max}s 0-60`}
              onRemove={() => onFilterChange({ accel060Max: undefined })}
            />
          )}
          {queryParams.quarterMileMax && (
            <FilterTag
              label={findThresholdLabel(meta?.quarterMileThresholds, queryParams.quarterMileMax) || `≤${queryParams.quarterMileMax}s 1/4mi`}
              onRemove={() => onFilterChange({ quarterMileMax: undefined })}
            />
          )}
          {queryParams.topSpeedMin && (
            <FilterTag
              label={findThresholdLabel(meta?.topSpeedThresholds, queryParams.topSpeedMin) || `≥${queryParams.topSpeedMin} mph`}
              onRemove={() => onFilterChange({ topSpeedMin: undefined })}
            />
          )}
        </div>
      )}
    </div>
  );
}
