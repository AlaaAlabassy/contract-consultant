import type { AskResponse } from "@/lib/api";
import ConfidenceBadge from "./ConfidenceBadge";

export type ChatTurn =
  | { role: "user"; text: string }
  | { role: "assistant"; response: AskResponse }
  | { role: "assistant-error"; text: string };

export default function MessageBubble({ turn }: { turn: ChatTurn }) {
  if (turn.role === "user") {
    return (
      <div className="flex justify-start">
        <div className="max-w-2xl rounded-2xl bg-blue-600 px-4 py-2 text-white">{turn.text}</div>
      </div>
    );
  }

  if (turn.role === "assistant-error") {
    return (
      <div className="flex justify-end">
        <div className="max-w-2xl rounded-2xl bg-red-50 px-4 py-2 text-red-700">{turn.text}</div>
      </div>
    );
  }

  const { answer_ar, confidence_label, citations } = turn.response;

  return (
    <div className="flex justify-end">
      <div className="max-w-2xl space-y-3 rounded-2xl bg-gray-100 px-4 py-3">
        <div className="flex items-center justify-between gap-2">
          <ConfidenceBadge label={confidence_label} />
        </div>
        <p className="leading-relaxed text-gray-900">{answer_ar}</p>

        {citations.length > 0 && (
          <div className="space-y-2 border-t border-gray-200 pt-2">
            {citations.map((citation, i) => (
              <div key={i} className="rounded-lg bg-white p-2 text-sm">
                <div className="text-gray-500">
                  {citation.filename} — البند {citation.clause_number}
                  {citation.page_number != null ? ` — صفحة ${citation.page_number}` : ""}
                </div>
                <blockquote dir="ltr" lang="en" className="mt-1 text-left italic text-gray-700">
                  “{citation.quote_en}”
                </blockquote>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
