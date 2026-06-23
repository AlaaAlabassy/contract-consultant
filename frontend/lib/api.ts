export type ConfidenceLabel = "high" | "warn" | "red" | "refuse";

export interface Citation {
  clause_number: string;
  page_number: number | null;
  filename: string;
  quote_en: string;
}

export interface AskResponse {
  conversation_id: string;
  answer_ar: string;
  confidence: number;
  confidence_label: ConfidenceLabel;
  citations: Citation[];
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export async function askQuestion(question: string, conversationId: string | null): Promise<AskResponse> {
  const response = await fetch(`${API_BASE_URL}/api/qa/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, conversation_id: conversationId }),
  });

  if (!response.ok) {
    throw new Error(`فشل الاتصال بالخادم (${response.status})`);
  }

  return response.json();
}
