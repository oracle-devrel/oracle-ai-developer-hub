export class NotFoundError extends Error {
  override name = "NotFoundError";
}

export class ProviderPhaseError extends Error {
  override name = "ProviderPhaseError";
  constructor(
    public readonly phase: "retrieval" | "generation" | "ingestion",
    message: string,
    options?: ErrorOptions,
  ) {
    super(message, options);
  }
}
