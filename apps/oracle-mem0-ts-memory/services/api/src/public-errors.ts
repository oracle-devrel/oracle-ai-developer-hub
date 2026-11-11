import { ZodError } from "zod";

export function publicError(error: unknown): { status: 400 | 404 | 500 | 502; body: { error: string; phase?: string } } {
  if (error instanceof ZodError) {
    return { status: 400, body: { error: error.issues[0]?.message || "Invalid request" } };
  }
  if (error && typeof error === "object" && "status" in error && error.status === 401 &&
      "code" in error && error.code === "expired_secret_key") {
    return { status: 502, body: { error: "The OpenAI API key has expired. Update OPENAI_API_KEY in this app's .env and restart the API." } };
  }
  if (error && typeof error === "object" && "status" in error && error.status === 429 &&
      "code" in error && error.code === "credit_balance_exhausted") {
    return { status: 502, body: { error: "There are no API credits remaining for the OpenAI organization linked to this key. Add credits to its billing account, then try again." } };
  }
  if (error && typeof error === "object" && "name" in error) {
    if (error.name === "NotFoundError") return { status: 404, body: { error: "Memory was not found" } };
    if (error.name === "ProviderPhaseError") {
      const phase = "phase" in error && typeof error.phase === "string" ? error.phase : "provider";
      return { status: 502, body: { error: `The ${phase} provider step failed`, phase } };
    }
  }
  return { status: 500, body: { error: "The request could not be completed" } };
}
