"use client";

import { useRef, useState } from "react";
import { askQuestion } from "@/lib/api";
import MessageBubble, { type ChatTurn } from "./MessageBubble";

export default function ChatWindow() {
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [question, setQuestion] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const conversationIdRef = useRef<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = question.trim();
    if (!trimmed || isLoading) return;

    setTurns((prev) => [...prev, { role: "user", text: trimmed }]);
    setQuestion("");
    setIsLoading(true);

    try {
      const response = await askQuestion(trimmed, conversationIdRef.current);
      conversationIdRef.current = response.conversation_id;
      setTurns((prev) => [...prev, { role: "assistant", response }]);
    } catch {
      setTurns((prev) => [
        ...prev,
        { role: "assistant-error", text: "تعذّر الاتصال بالخادم. يرجى المحاولة مرة أخرى." },
      ]);
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="mx-auto flex h-full max-w-3xl flex-col p-4">
      <div className="flex-1 space-y-3 overflow-y-auto">
        {turns.length === 0 && (
          <p className="text-gray-500">اطرح سؤالاً عن أحد العقود المستوعبة لتبدأ المحادثة.</p>
        )}
        {turns.map((turn, i) => (
          <MessageBubble key={i} turn={turn} />
        ))}
        {isLoading && <p className="text-sm text-gray-500">...جارٍ البحث في العقد</p>}
      </div>

      <form onSubmit={handleSubmit} className="mt-4 flex gap-2">
        <input
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="اكتب سؤالك هنا..."
          disabled={isLoading}
          className="flex-1 rounded-full border border-gray-300 px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <button
          type="submit"
          disabled={isLoading || !question.trim()}
          className="rounded-full bg-blue-600 px-5 py-2 text-white disabled:opacity-50"
        >
          إرسال
        </button>
      </form>
    </div>
  );
}
