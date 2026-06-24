import type { Severity } from "@/lib/api";

const STYLES: Record<Severity, { text: string; classes: string }> = {
  high: { text: "خطورة مرتفعة", classes: "bg-red-100 text-red-800" },
  medium: { text: "خطورة متوسطة", classes: "bg-orange-100 text-orange-800" },
  low: { text: "خطورة منخفضة", classes: "bg-yellow-100 text-yellow-800" },
};

export default function SeverityBadge({ severity }: { severity: Severity }) {
  const { text, classes } = STYLES[severity] ?? STYLES.medium;
  return <span className={`rounded-full px-3 py-1 text-xs font-medium ${classes}`}>{text}</span>;
}
