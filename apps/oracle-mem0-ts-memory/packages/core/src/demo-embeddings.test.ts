import { describe, expect, it } from "vitest";
import { DemoEmbeddings } from "./demo-embeddings.js";

describe("DemoEmbeddings", () => {
  it("returns repeatable 24-dimensional unit vectors without a service", async () => {
    const embeddings = new DemoEmbeddings();
    const first = await embeddings.embedQuery("Masala tea without sugar");
    expect(first).toEqual(await embeddings.embedQuery("masala tea without sugar"));
    expect(first).toHaveLength(24);
    expect(Math.hypot(...first)).toBeCloseTo(1, 4);
    expect(await embeddings.embedDocuments(["Masala tea without sugar"])).toEqual([first]);
  });

  it("puts a related question closer than an unrelated one", async () => {
    const embeddings = new DemoEmbeddings();
    const query = await embeddings.embedQuery("What drink do I prefer?");
    const tea = await embeddings.embedQuery("User 1 prefers masala tea without sugar.");
    const seat = await embeddings.embedQuery("User 1 likes window seats when travelling.");
    const similarity = (other: number[]) => query.reduce((sum, value, index) => sum + value * other[index]!, 0);
    expect(similarity(tea)).toBeGreaterThan(similarity(seat));
  });

  it("treats singular and plural meeting terms as the same topic", async () => {
    const embeddings = new DemoEmbeddings();
    const query = await embeddings.embedQuery("afternoon meeting");
    const exactPreference = await embeddings.embedQuery("User 2 prefers afternoon meetings.");
    const otherMeeting = await embeddings.embedQuery("User 2 prefers concise meeting summaries with action items.");
    const similarity = (other: number[]) => query.reduce((sum, value, index) => sum + value * other[index]!, 0);

    expect(similarity(exactPreference)).toBeGreaterThan(similarity(otherMeeting));
  });
});
