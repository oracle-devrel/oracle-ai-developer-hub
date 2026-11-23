export type DemoMemory = {
  userId: "user-1" | "user-2";
  text: string;
  category: "food" | "travel" | "schedule" | "communication" | "work";
};

/** Reviewable sample data loaded into Oracle by the demo seed workflow. */
export const DEMO_MEMORIES = [
  { userId: "user-1", text: "User 1 prefers masala tea without sugar.", category: "food" },
  { userId: "user-1", text: "User 1 likes window seats when travelling.", category: "travel" },
  { userId: "user-1", text: "User 1 avoids meetings before 9:30 AM.", category: "schedule" },
  { userId: "user-1", text: "User 1 prefers step-by-step explanations with practical examples.", category: "communication" },
  { userId: "user-1", text: "User 1 prefers a quiet workspace for focused tasks.", category: "work" },
  { userId: "user-2", text: "User 2 is vegetarian and enjoys spicy food.", category: "food" },
  { userId: "user-2", text: "User 2 prefers aisle seats on long flights.", category: "travel" },
  { userId: "user-2", text: "User 2 prefers meetings after 2:00 PM.", category: "schedule" },
  { userId: "user-2", text: "User 2 prefers concise meeting summaries with action items.", category: "communication" },
  { userId: "user-2", text: "User 2 prefers dark mode and keyboard shortcuts while working.", category: "work" },
] as const satisfies readonly DemoMemory[];
