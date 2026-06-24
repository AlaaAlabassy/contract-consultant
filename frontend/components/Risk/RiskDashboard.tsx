"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  getRiskResults,
  getRiskScanStatus,
  listContracts,
  triggerRiskScan,
  type ContractSummary,
  type JobStatus,
  type RiskResultRow,
  type Severity,
} from "@/lib/api";
import IngestionPanel from "@/components/Ingestion/IngestionPanel";
import RiskFindingCard, { type GroupedFinding } from "./RiskFindingCard";

const SEVERITY_ORDER: Record<Severity, number> = { high: 0, medium: 1, low: 2 };

// One backend RiskResult row exists per (rule, cited clause); collapse them back
// into one card per rule, gathering that rule's clause citations.
function groupFindings(rows: RiskResultRow[]): GroupedFinding[] {
  const byRule = new Map<string, GroupedFinding>();
  for (const row of rows) {
    const existing = byRule.get(row.rule_key);
    const citation = { clause_number: row.clause_number, page_number: row.page_number };
    if (existing) {
      existing.citations.push(citation);
    } else {
      byRule.set(row.rule_key, {
        rule_key: row.rule_key,
        severity: row.severity,
        explanation_ar: row.explanation_ar,
        confidence: row.confidence,
        citations: [citation],
      });
    }
  }
  return [...byRule.values()].sort(
    (a, b) => SEVERITY_ORDER[a.severity] - SEVERITY_ORDER[b.severity],
  );
}

export default function RiskDashboard() {
  const [contracts, setContracts] = useState<ContractSummary[] | null>(null);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [results, setResults] = useState<RiskResultRow[] | null>(null);
  const [scan, setScan] = useState<JobStatus>({ status: "idle" });
  const [polling, setPolling] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadContracts = useCallback(async () => {
    try {
      setContracts(await listContracts());
    } catch {
      setError("تعذّر جلب قائمة العقود.");
    }
  }, []);

  useEffect(() => {
    loadContracts();
  }, [loadContracts]);

  // Poll scan status while a scan is running, then pull the persisted results.
  useEffect(() => {
    if (!polling || selectedId == null) return;
    const interval = setInterval(async () => {
      try {
        const s = await getRiskScanStatus(selectedId);
        setScan(s);
        if (s.status === "done" || s.status === "error") {
          setPolling(false);
          if (s.status === "done") setResults(await getRiskResults(selectedId));
        }
      } catch {
        setPolling(false);
        setError("انقطع الاتصال أثناء متابعة الفحص.");
      }
    }, 3000);
    return () => clearInterval(interval);
  }, [polling, selectedId]);

  async function handleSelect(id: number) {
    setSelectedId(id);
    setResults(null);
    setScan({ status: "idle" });
    setPolling(false);
    setError(null);
    try {
      setResults(await getRiskResults(id));
    } catch {
      setResults([]);
    }
  }

  async function handleScan() {
    if (selectedId == null) return;
    setError(null);
    setResults(null);
    setScan({ status: "running" });
    try {
      await triggerRiskScan(selectedId);
      setPolling(true);
    } catch {
      setScan({ status: "error" });
      setError("تعذّر بدء فحص المخاطر.");
    }
  }

  const grouped = useMemo(() => (results ? groupFindings(results) : []), [results]);
  const scanning = polling || scan.status === "running";

  return (
    <div className="mx-auto h-full max-w-3xl space-y-6 overflow-y-auto p-4">
      <IngestionPanel onIngested={loadContracts} />

      <section className="space-y-3">
        <h2 className="font-bold text-gray-900">العقود المستوعَبة</h2>
        {contracts === null && <p className="text-sm text-gray-500">...جارٍ التحميل</p>}
        {contracts !== null && contracts.length === 0 && (
          <p className="text-sm text-gray-500">لا توجد عقود مستوعَبة بعد. شغّل الاستيعاب أولاً.</p>
        )}
        <div className="space-y-2">
          {contracts?.map((c) => (
            <button
              key={c.id}
              onClick={() => handleSelect(c.id)}
              className={`flex w-full items-center justify-between gap-2 rounded-xl border px-4 py-3 text-right transition-colors ${
                selectedId === c.id
                  ? "border-blue-600 bg-blue-50"
                  : "border-gray-200 bg-white hover:bg-gray-50"
              }`}
            >
              <span className="font-medium text-gray-900">{c.filename}</span>
              {c.page_count != null && (
                <span className="text-xs text-gray-400">{c.page_count} صفحة</span>
              )}
            </button>
          ))}
        </div>
      </section>

      {selectedId != null && (
        <section className="space-y-4">
          <div className="flex items-center justify-between gap-2">
            <h2 className="font-bold text-gray-900">المخاطر المكتشفة</h2>
            <button
              onClick={handleScan}
              disabled={scanning}
              className="rounded-full bg-blue-600 px-5 py-2 text-sm text-white disabled:opacity-50"
            >
              {scanning ? "...جارٍ الفحص" : results && results.length > 0 ? "إعادة الفحص" : "بدء الفحص"}
            </button>
          </div>

          {scanning && (
            <p className="text-sm text-gray-500">...جارٍ فحص العقد مقابل قائمة المخاطر</p>
          )}
          {error && <p className="text-sm text-red-700">{error}</p>}

          {!scanning && results !== null && results.length === 0 && (
            <p className="text-sm text-gray-500">
              لا توجد نتائج محفوظة لهذا العقد. اضغط «بدء الفحص» لتشغيل فحص المخاطر.
            </p>
          )}

          <div className="space-y-3">
            {grouped.map((finding) => (
              <RiskFindingCard key={finding.rule_key} finding={finding} />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
