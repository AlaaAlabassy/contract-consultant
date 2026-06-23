import type { ConfidenceLabel } from "@/lib/api";

const STYLES: Record<ConfidenceLabel, { text: string; classes: string }> = {
  high: { text: "ثقة عالية", classes: "bg-green-100 text-green-800" },
  warn: { text: "ثقة متوسطة", classes: "bg-yellow-100 text-yellow-800" },
  red: { text: "ثقة منخفضة", classes: "bg-orange-100 text-orange-800" },
  refuse: { text: "لا توجد ثقة كافية", classes: "bg-red-100 text-red-800" },
};

export default function ConfidenceBadge({ label }: { label: ConfidenceLabel }) {
  const { text, classes } = STYLES[label];
  return <span className={`rounded-full px-3 py-1 text-xs font-medium ${classes}`}>{text}</span>;
}
