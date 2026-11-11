import { z } from "zod";

import type { JsonValue } from "./contracts.js";

const userId = z.string().trim().min(1, "User id is required").max(128);
const text = z.string().trim().min(1, "Memory text is required").max(10_000);

const jsonValue: z.ZodType<JsonValue> = z.lazy(() =>
  z.union([
    z.string(),
    z.number().finite(),
    z.boolean(),
    z.null(),
    z.array(jsonValue),
    z.record(jsonValue),
  ]),
);

export const metadataSchema = z.record(jsonValue).default({});

export const chatRequestSchema = z.object({
  userId,
  message: z.string().trim().min(1, "Message is required").max(10_000),
});

export const memoryCreateSchema = z.object({
  userId,
  text,
  metadata: metadataSchema.optional().default({}),
});

export const memoryUpdateSchema = z.object({
  userId,
  text,
});

export const memoryQuerySchema = z.object({
  userId,
  query: z.string().trim().max(2_000).optional(),
  limit: z.coerce.number().int().min(1).max(20).optional().default(10),
});
