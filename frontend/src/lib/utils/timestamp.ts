export function timestampToSeconds(timestamp: string): number {
  if (typeof timestamp !== "string" || timestamp.length === 0) {
    return 0;
  }

  const parts = timestamp.split(":").map((value) => Number(value));
  if (parts.some((value) => Number.isNaN(value) || value < 0)) {
    return 0;
  }

  if (parts.length === 3) {
    return parts[0] * 3600 + parts[1] * 60 + parts[2];
  }

  if (parts.length === 2) {
    return parts[0] * 60 + parts[1];
  }

  return 0;
}
