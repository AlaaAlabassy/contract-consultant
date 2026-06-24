"use client";

import { useEffect, useState } from "react";
import { getIngestionStatus, triggerIngestion, type JobStatus } from "@/lib/api";

const STATUS_TEXT: Record<JobStatus["status"], string> = {
  idle: "خامل",
  running: "جارٍ الاستيعاب...",
  done: "اكتمل",
  error: "فشل",
};

const STATUS_CLASSES: Record<JobStatus["status"], string> = {
  idle: "bg-gray-100 text-gray-700",
  running: "bg-blue-100 text-blue-800",
  done: "bg-green-100 text-green-800",
  error: "bg-red-100 text-red-800",
};

export default function IngestionPanel({ onIngested }: { onIngested?: () => void }) {
  const [status, setStatus] = useState<JobStatus>({ status: "idle" });
  const [polling, setPolling] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load current status once on mount; if a run is already in progress, resume polling.
  useEffect(() => {
    getIngestionStatus()
      .then((s) => {
        setStatus(s);
        if (s.status === "running") setPolling(true);
      })
      .catch(() => setError("تعذّر الاتصال بالخادم."));
  }, []);

  useEffect(() => {
    if (!polling) return;
    const interval = setInterval(async () => {
      try {
        const s = await getIngestionStatus();
        setStatus(s);
        if (s.status === "done" || s.status === "error") {
          setPolling(false);
          if (s.status === "done") onIngested?.();
        }
      } catch {
        setPolling(false);
        setError("انقطع الاتصال أثناء متابعة الاستيعاب.");
      }
    }, 3000);
    return () => clearInterval(interval);
  }, [polling, onIngested]);

  async function handleRun() {
    setError(null);
    setStatus({ status: "running" });
    try {
      await triggerIngestion();
      setPolling(true);
    } catch {
      setStatus({ status: "error" });
      setError("تعذّر بدء الاستيعاب.");
    }
  }

  const summary = status.summary;

  return (
    <section className="space-y-3 rounded-2xl border border-gray-200 bg-white p-4">
      <div className="flex items-center justify-between gap-2">
        <h2 className="font-bold text-gray-900">استيعاب العقود من Google Drive</h2>
        <span className={`rounded-full px-3 py-1 text-xs font-medium ${STATUS_CLASSES[status.status]}`}>
          {STATUS_TEXT[status.status]}
        </span>
      </div>

      <button
        onClick={handleRun}
        disabled={polling || status.status === "running"}
        className="rounded-full bg-blue-600 px-5 py-2 text-sm text-white disabled:opacity-50"
      >
        {polling || status.status === "running" ? "...جارٍ الاستيعاب" : "تشغيل الاستيعاب"}
      </button>

      {error && <p className="text-sm text-red-700">{error}</p>}

      {summary && (
        <div className="flex flex-wrap gap-2 text-sm">
          <span className="rounded-lg bg-green-50 px-3 py-1 text-green-800">
            مستوعَب: {summary.ingested?.length ?? 0}
          </span>
          <span className="rounded-lg bg-gray-50 px-3 py-1 text-gray-700">
            متخطّى: {summary.skipped?.length ?? 0}
          </span>
          <span className="rounded-lg bg-red-50 px-3 py-1 text-red-800">
            فشل: {summary.failed?.length ?? 0}
          </span>
        </div>
      )}

      {summary?.error && <p className="text-sm text-red-700">{summary.error}</p>}

      {summary?.failed && summary.failed.length > 0 && (
        <ul className="space-y-1 text-xs text-gray-500">
          {summary.failed.map((f, i) => (
            <li key={i}>
              {f.name}
              {f.reason ? ` — ${f.reason}` : ""}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
