export function minutesToTimeLabel(minutesSinceParkOpen: number, parkOpenHour = 9): string {
  const total = parkOpenHour * 60 + minutesSinceParkOpen;
  const h = Math.floor(total / 60) % 24;
  const m = total % 60;
  const ampm = h >= 12 ? "PM" : "AM";
  const h12 = ((h + 11) % 12) + 1;
  return `${h12}:${m.toString().padStart(2, "0")} ${ampm}`;
}

export function formatHM(minutes: number): string {
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  if (h === 0) return `${m}m`;
  if (m === 0) return `${h}h`;
  return `${h}h ${m}m`;
}

export function landAccent(color: string): React.CSSProperties {
  return { borderLeft: `4px solid ${color}` };
}
