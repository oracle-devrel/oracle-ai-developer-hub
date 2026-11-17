/** Small, repeatable vectors for exercising Oracle search without a model service. */
export class DemoEmbeddings {
  readonly dimensions = 24;

  private readonly topicTerms = [
    /\b(tea|coffee|drink|beverage|masala)\b/g,
    /\b(sugar|sweet|unsweetened)\b/g,
    /\b(travel|travelling|trip|flight|seat|window)\b/g,
    /\b(food|lunch|dinner|meal|order|vegetarian|vegetable)\b/g,
    /\b(spicy|spice|hot)\b/g,
    /\b(meetings?|notes?|summar(?:y|ies)|actions?|items?)\b/g,
    /\b(work|working|format|concise)\b/g,
    /\b(prefer|prefers|preference|preferences|like|likes)\b/g,
  ];

  private vector(text: string): number[] {
    const lower = text.toLowerCase();
    const vector = Array<number>(this.dimensions).fill(0);
    this.topicTerms.forEach((pattern, index) => {
      // A topic is a feature, not a keyword-count score. This prevents a
      // sentence with several meeting words from overwhelming a closer match.
      vector[index] = new RegExp(pattern.source).test(lower) ? 1 : 0;
    });
    for (const token of lower.match(/[a-z0-9]+/g) ?? []) {
      let hash = 0;
      for (const char of token) hash = (hash * 31 + char.charCodeAt(0)) >>> 0;
      vector[8 + (hash % 16)]! += 0.15;
    }
    // Oracle cosine distance needs a non-zero vector, including for punctuation-only input.
    if (!vector.some((value) => value > 0)) vector[23] = 1;
    const norm = Math.hypot(...vector);
    return vector.map((value) => Number((value / norm).toFixed(6)));
  }

  async embedQuery(text: string): Promise<number[]> {
    return this.vector(text);
  }

  async embedDocuments(texts: string[]): Promise<number[][]> {
    return texts.map((text) => this.vector(text));
  }
}
