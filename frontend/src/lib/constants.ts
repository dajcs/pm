export const PRIORITIES = ["none", "low", "medium", "high", "urgent"];

export const LABEL_OPTIONS = ["bug", "feature", "improvement", "docs", "testing", "blocked"];

export const LABEL_COLORS: Record<string, string> = {
  bug: "bg-red-100 text-red-700 border-red-200",
  feature: "bg-blue-100 text-blue-700 border-blue-200",
  improvement: "bg-purple-100 text-purple-700 border-purple-200",
  docs: "bg-gray-100 text-gray-700 border-gray-200",
  testing: "bg-green-100 text-green-700 border-green-200",
  blocked: "bg-orange-100 text-orange-700 border-orange-200",
};

export const PRIORITY_STYLES: Record<string, { dot: string; label: string }> = {
  none:   { dot: "bg-[var(--gray-text)]", label: "none" },
  low:    { dot: "bg-[var(--primary-blue)]", label: "low" },
  medium: { dot: "bg-[var(--accent-yellow)]", label: "medium" },
  high:   { dot: "bg-orange-500", label: "high" },
  urgent: { dot: "bg-red-500", label: "urgent" },
};

export function formatRelative(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}
