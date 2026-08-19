/** Monotonic, high-resolution clock used only after both images are rendered. */
export function reactionNow(): number {
  return performance.now();
}

export function elapsedMilliseconds(startedAt: number): number {
  return Math.max(0, reactionNow() - startedAt);
}

export function measureTimerResolution(samples = 20_000): number | null {
  let previous = reactionNow();
  let smallest = Number.POSITIVE_INFINITY;
  for (let index = 0; index < samples; index += 1) {
    const current = reactionNow();
    const difference = current - previous;
    if (difference > 0 && difference < smallest) smallest = difference;
    previous = current;
  }
  return Number.isFinite(smallest) ? smallest : null;
}
