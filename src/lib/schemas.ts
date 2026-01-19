import { z } from "zod";

export const carsQuerySchema = z.object({
  page: z.coerce.number().int().min(1).optional().default(1),
  pageSize: z.coerce.number().int().min(1).max(100).optional().default(50),
  sortBy: z.string().optional(),
  sortOrder: z.enum(["asc", "desc"]).optional().default("asc"),
  manufacturer: z.string().optional(),
  country: z.string().optional(),
  yearMin: z.coerce.number().int().optional(),
  yearMax: z.coerce.number().int().optional(),
  search: z.string().optional(),
  source: z.string().optional(),
  // New categorical filters
  bodyStyle: z.string().optional(),
  propulsion: z.string().optional(),
  engineType: z.string().optional(),
  engineAspiration: z.string().optional(),
  enginePlacement: z.string().optional(),
  drivetrain: z.string().optional(),
  // Threshold filters
  displacementMin: z.coerce.number().optional(),
  powerMin: z.coerce.number().optional(),
  torqueMin: z.coerce.number().optional(),
  weightMax: z.coerce.number().optional(),
  powerToWeightMax: z.coerce.number().optional(),
  accel060Max: z.coerce.number().optional(),
  quarterMileMax: z.coerce.number().optional(),
  topSpeedMin: z.coerce.number().optional(),
});

export type CarsQuery = z.infer<typeof carsQuerySchema>;

export const paginationSchema = z.object({
  page: z.number().int().min(1),
  pageSize: z.number().int().min(1).max(100),
  totalCount: z.number().int().min(0),
  totalPages: z.number().int().min(0),
});

export type Pagination = z.infer<typeof paginationSchema>;
