import type { Severity } from "@/lib/api";
import SeverityBadge from "./SeverityBadge";

export interface GroupedFinding {
  rule_key: string;
  severity: Severity;
  explanation_ar: string;
  confidence: number;
  citations: { clause_number: string | null; page_number: number | null }[];
}

// Arabic display titles for each rule_key in backend app/risk/catalog.py.
const RULE_TITLES: Record<string, string> = {
  unlimited_liability: "مسؤولية غير محدودة",
  uncapped_liquidated_damages: "غرامات تأخير بلا حد أعلى",
  unilateral_termination: "إنهاء أحادي الجانب",
  narrow_force_majeure: "تعريف ضيّق للقوة القاهرة",
  no_extension_of_time: "غياب آلية تمديد المدة",
  unilateral_variation: "تغييرات أحادية الجانب",
  excessive_retention: "احتجاز مرتفع",
  unfavorable_payment_terms: "شروط سداد مجحفة",
  one_sided_indemnification: "تعويض أحادي الجانب",
  no_dispute_resolution: "غياب آلية تسوية النزاعات",
};

export default function RiskFindingCard({ finding }: { finding: GroupedFinding }) {
  const title = RULE_TITLES[finding.rule_key] ?? finding.rule_key;

  return (
    <div className="space-y-3 rounded-2xl border border-gray-200 bg-white p-4 shadow-sm">
      <div className="flex items-center justify-between gap-2">
        <h3 className="font-bold text-gray-900">{title}</h3>
        <SeverityBadge severity={finding.severity} />
      </div>

      <p className="leading-relaxed text-gray-800">{finding.explanation_ar}</p>

      <div className="flex flex-wrap gap-2 border-t border-gray-100 pt-2">
        {finding.citations.map((c, i) => (
          <span key={i} className="rounded-lg bg-gray-100 px-2 py-1 text-xs text-gray-600">
            {c.clause_number ? `البند ${c.clause_number}` : "بند غير مرقّم"}
            {c.page_number != null ? ` — صفحة ${c.page_number}` : ""}
          </span>
        ))}
      </div>

      <div className="text-xs text-gray-400">الثقة: {Math.round(finding.confidence * 100)}%</div>
    </div>
  );
}
