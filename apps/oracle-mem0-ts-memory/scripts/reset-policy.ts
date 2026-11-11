export function canResetWithoutPrompt(argv: readonly string[], _isTTY: boolean): boolean {
  return argv.includes("--yes");
}
