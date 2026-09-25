import { z } from "zod";

export const QueryStrategySchema = z.enum(["sql", "vector", "hybrid"]);
export const DataChatIntentSchema = z.enum([
  "revenueTrend",
  "topAccounts",
  "activeUsers",
  "contractSearch",
  "marchDip"
]);

export const UiComponentTypeSchema = z.enum([
  "lineChart",
  "areaChart",
  "barChart",
  "horizontalBarChart",
  "pieChart",
  "comparisonTable",
  "kpiCard",
  "sourceCards",
  "mixedInsight"
]);

export const DataChatPlanSchema = z.object({
  intent: DataChatIntentSchema,
  strategy: QueryStrategySchema,
  title: z.string().trim().min(1).max(120),
  componentTypes: z.array(UiComponentTypeSchema).min(1).max(6)
});

const ChartDatumSchema = z.record(z.union([z.string(), z.number()]));

const LineChartSchema = z.object({
  type: z.literal("lineChart"),
  title: z.string().min(1),
  description: z.string().optional(),
  xKey: z.string().min(1),
  yKey: z.string().min(1),
  data: z.array(ChartDatumSchema)
});

const AreaChartSchema = z.object({
  type: z.literal("areaChart"),
  title: z.string().min(1),
  description: z.string().optional(),
  categoryKey: z.string().min(1),
  data: z.array(ChartDatumSchema)
});

const BarChartSchema = z.object({
  type: z.literal("barChart"),
  title: z.string().min(1),
  description: z.string().optional(),
  categoryKey: z.string().min(1),
  variant: z.enum(["grouped", "stacked"]).default("grouped"),
  data: z.array(ChartDatumSchema)
});

const HorizontalBarChartSchema = z.object({
  type: z.literal("horizontalBarChart"),
  title: z.string().min(1),
  description: z.string().optional(),
  categoryKey: z.string().min(1),
  variant: z.enum(["grouped", "stacked"]).default("grouped"),
  data: z.array(ChartDatumSchema)
});

const PieChartSchema = z.object({
  type: z.literal("pieChart"),
  title: z.string().min(1),
  description: z.string().optional(),
  categoryKey: z.string().min(1),
  dataKey: z.string().min(1),
  variant: z.enum(["pie", "donut"]).default("donut"),
  data: z.array(ChartDatumSchema)
});

const ComparisonTableSchema = z.object({
  type: z.literal("comparisonTable"),
  title: z.string().min(1),
  columns: z.array(
    z.object({
      key: z.string().min(1),
      label: z.string().min(1),
      align: z.enum(["left", "right"]).optional()
    })
  ),
  rows: z.array(z.record(z.union([z.string(), z.number(), z.null()])))
});

const KpiCardSchema = z.object({
  type: z.literal("kpiCard"),
  title: z.string().min(1),
  value: z.string().min(1),
  delta: z.string().min(1),
  trend: z.enum(["up", "down", "flat"]),
  caption: z.string().min(1)
});

const SourceSchema = z.object({
  id: z.union([z.string(), z.number()]),
  title: z.string().min(1),
  account: z.string().min(1),
  snippet: z.string().min(1),
  citation: z.string().min(1),
  score: z.number().min(0).max(1).optional()
});

const SourceCardsSchema = z.object({
  type: z.literal("sourceCards"),
  title: z.string().min(1),
  sources: z.array(SourceSchema)
});

const MixedInsightSchema = z.object({
  type: z.literal("mixedInsight"),
  title: z.string().min(1),
  callout: z.string().min(1),
  chart: LineChartSchema,
  sources: SourceCardsSchema,
  bullets: z.array(z.string().min(1)).min(1).max(5)
});

export const UiComponentSchema = z.discriminatedUnion("type", [
  LineChartSchema,
  AreaChartSchema,
  BarChartSchema,
  HorizontalBarChartSchema,
  PieChartSchema,
  ComparisonTableSchema,
  KpiCardSchema,
  SourceCardsSchema,
  MixedInsightSchema
]);

export const DataChatResponseSchema = z.object({
  title: z.string().min(1),
  summary: z.string().min(1),
  components: z.array(UiComponentSchema).min(1)
});

export const QueryTraceSchema = z.object({
  strategy: QueryStrategySchema,
  label: z.string().min(1),
  statement: z.string().min(1),
  elapsedMs: z.number().int().nonnegative(),
  rowCount: z.number().int().nonnegative()
});

export const DataChatApiRequestSchema = z.object({
  message: z.string().trim().min(1).max(2_000)
});

export const DataChatApiResponseSchema = z.object({
  answer: DataChatResponseSchema,
  queryTrace: z.array(QueryTraceSchema).min(1)
});

export type DataChatPlan = z.infer<typeof DataChatPlanSchema>;
export type UiComponent = z.infer<typeof UiComponentSchema>;
export type DataChatResponse = z.infer<typeof DataChatResponseSchema>;
export type QueryTrace = z.infer<typeof QueryTraceSchema>;
export type DataChatApiRequest = z.infer<typeof DataChatApiRequestSchema>;
export type DataChatApiResponse = z.infer<typeof DataChatApiResponseSchema>;
