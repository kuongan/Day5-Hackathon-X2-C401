import React, { useEffect, useMemo, useRef, useState } from "react";

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

const AGENTS = [
  {
    id: "orchestration",
    label: "Orchestration",
    description: "Tự động phân luồng câu hỏi sang agent phù hợp."
  },
  {
    id: "chat",
    label: "Disease QA",
    description: "Hỏi đáp bệnh lý từ dữ liệu y khoa."
  },
  {
    id: "medicine",
    label: "Medicine QA",
    description: "Tra cứu thuốc và thông tin sử dụng."
  },
  {
    id: "booking",
    label: "Booking",
    description: "Đặt lịch khám theo ngữ cảnh hội thoại."
  }
];

const ENDPOINTS = {
  orchestration: "/api/v1/orchestration",
  chat: "/api/v1/chat",
  medicine: "/api/v1/medicine",
  booking: "/api/v1/booking"
};

const QUICK_PROMPTS = [
  "Triệu chứng sốt cao có nguy hiểm không?",
  "Thuốc paracetamol dùng cho trẻ 5 tuổi như thế nào?",
  "Tôi muốn đặt lịch khám với bác sĩ tim mạch tuần này.",
  "Tôi bị ho kéo dài, nên đi khám gì?"
];

const AGENT_CAPABILITIES = {
  orchestration: [
    "Tự động phân loại ý định người dùng.",
    "Gọi các agent phù hợp để tổng hợp câu trả lời.",
    "Báo lại intent, tuyến xử lý và kết quả delegate."
  ],
  chat: [
    "Hỏi đáp bệnh lý từ dữ liệu y khoa đã lập chỉ mục.",
    "Trả lời kèm nguồn tham khảo.",
    "Phù hợp cho câu hỏi triệu chứng, bệnh học."
  ],
  medicine: [
    "Tra cứu thông tin thuốc và chỉ định sử dụng.",
    "Trả lời kèm nguồn tham khảo.",
    "Phù hợp cho câu hỏi về liều dùng, lưu ý thuốc."
  ],
  booking: [
    "Tạo lịch hẹn khám theo hội thoại.",
    "Xác nhận lịch và trả về mã appointment.",
    "Phù hợp cho đặt lịch khám bác sĩ."
  ]
};

function buildAgentIntro(agentId, agentLabel, agentDescription) {
  const capabilityList = AGENT_CAPABILITIES[agentId] || [];
  const lines = capabilityList.map((item) => `• ${item}`).join("\n");
  return {
    id: `intro-${agentId}-${Date.now()}`,
    role: "assistant",
    content: `Bạn đang dùng ${agentLabel}.\n${agentDescription}\n\nKhả năng hỗ trợ:\n${lines}`,
    meta: { type: "system" }
  };
}

function formatResponse(mode, payload) {
  if (mode === "booking") {
    if (payload?.success) {
      return {
        text: `Đặt lịch thành công. Mã lịch hẹn: ${payload.appointment_id ?? "N/A"}.`,
        meta: {
          type: "booking",
          raw: payload
        }
      };
    }
    return {
      text: payload?.error || "Đặt lịch thất bại. Vui lòng thử lại.",
      meta: {
        type: "booking",
        raw: payload
      }
    };
  }

  if (mode === "orchestration") {
    const details = [];
    if (payload?.intent) {
      details.push(`Intent: ${payload.intent}`);
    }
    if (payload?.route_to?.length) {
      details.push(`Route: ${payload.route_to.join(", ")}`);
    }
    if (payload?.error) {
      details.push(`Error: ${payload.error}`);
    }

    return {
      text: payload?.answer || "Chưa có câu trả lời.",
      meta: {
        type: "orchestration",
        details,
        delegated: payload?.delegated_results || []
      }
    };
  }

  return {
    text: payload?.answer || "Chưa có câu trả lời.",
    meta: {
      type: "qa",
      sources: payload?.sources || []
    }
  };
}

export default function App() {
  const [agent, setAgent] = useState("orchestration");
  const [conversationId, setConversationId] = useState("default");
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState(() => [
    {
      id: "welcome",
      role: "assistant",
      content: "Xin chào! Hỏi mình về bệnh lý, thuốc hoặc đặt lịch khám nhé.",
      meta: {
        type: "system"
      }
    }
  ]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const listRef = useRef(null);

  const activeAgent = useMemo(
    () => AGENTS.find((item) => item.id === agent),
    [agent]
  );

  useEffect(() => {
    if (!activeAgent) return;
    setMessages([
      buildAgentIntro(activeAgent.id, activeAgent.label, activeAgent.description)
    ]);
    setInput("");
    setError("");
    setLoading(false);
  }, [activeAgent]);

  const scrollToBottom = () => {
    requestAnimationFrame(() => {
      if (listRef.current) {
        listRef.current.scrollTop = listRef.current.scrollHeight;
      }
    });
  };

  const sendMessage = async (text) => {
    const trimmed = text.trim();
    if (!trimmed || loading) return;

    const userMessage = {
      id: `user-${Date.now()}`,
      role: "user",
      content: trimmed
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setError("");
    setLoading(true);
    scrollToBottom();

    try {
      const response = await fetch(`${API_BASE}${ENDPOINTS[agent]}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          question: trimmed,
          conversation_id: conversationId || "default"
        })
      });

      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload?.detail || "Backend error");
      }

      const formatted = formatResponse(agent, payload);
      const assistantMessage = {
        id: `assistant-${Date.now()}`,
        role: "assistant",
        content: formatted.text,
        meta: formatted.meta
      };
      setMessages((prev) => [...prev, assistantMessage]);
      scrollToBottom();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Có lỗi xảy ra";
      setError(message);
      setMessages((prev) => [
        ...prev,
        {
          id: `assistant-error-${Date.now()}`,
          role: "assistant",
          content: `Xin lỗi, không thể xử lý yêu cầu. ${message}`,
          meta: { type: "error" }
        }
      ]);
      scrollToBottom();
    } finally {
      setLoading(false);
    }
  };

  const onSubmit = (event) => {
    event.preventDefault();
    sendMessage(input);
  };

  const onKeyDown = (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      sendMessage(input);
    }
  };

  return (
    <div className="min-h-screen">
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-6 px-4 pb-10 pt-10 lg:flex-row">
        <section className="w-full max-w-xl space-y-6">
          <div className="rounded-3xl border border-white/10 bg-white/5 p-6 shadow-panel">
            <p className="font-display text-sm uppercase tracking-[0.3em] text-glow/70">
              Medical Assistant
            </p>
            <h1 className="mt-3 font-display text-3xl font-semibold text-white md:text-4xl">
              Chatbot hỗ trợ tra cứu bệnh lý, thuốc và đặt lịch.
            </h1>
            <p className="mt-3 text-base text-mist/80">
              Chọn agent phù hợp, nhập câu hỏi và theo dõi phản hồi theo thời gian thực.
            </p>
          </div>

          <div className="rounded-3xl border border-white/10 bg-white/5 p-6 shadow-float">
            <div className="flex items-center justify-between">
              <h2 className="font-display text-lg text-white">Cấu hình</h2>
              <span className="rounded-full border border-white/10 px-3 py-1 text-xs text-mist/70">
                API: {API_BASE}
              </span>
            </div>
            <div className="mt-4 space-y-4">
              <label className="block text-sm text-mist/70">Chọn agent</label>
              <div className="grid gap-3">
                {AGENTS.map((item) => (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => setAgent(item.id)}
                    className={`rounded-2xl border px-4 py-3 text-left transition ${
                      agent === item.id
                        ? "border-glow/60 bg-white/10 text-white"
                        : "border-white/10 bg-white/5 text-mist/70 hover:border-glow/40"
                    }`}
                  >
                    <div className="font-display text-sm font-semibold">
                      {item.label}
                    </div>
                    <p className="mt-1 text-xs text-mist/70">{item.description}</p>
                  </button>
                ))}
              </div>

              <div>
                <label className="block text-sm text-mist/70" htmlFor="conversationId">
                  Conversation ID
                </label>
                <input
                  id="conversationId"
                  value={conversationId}
                  onChange={(event) => setConversationId(event.target.value)}
                  className="mt-2 w-full rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-white outline-none ring-0 focus:border-glow/60"
                  placeholder="default"
                />
              </div>
            </div>
          </div>

          <div className="rounded-3xl border border-white/10 bg-white/5 p-6">
            <h3 className="font-display text-sm uppercase tracking-[0.3em] text-glow/70">
              Gợi ý nhanh
            </h3>
            <div className="mt-4 flex flex-wrap gap-2">
              {QUICK_PROMPTS.map((prompt) => (
                <button
                  key={prompt}
                  type="button"
                  onClick={() => sendMessage(prompt)}
                  className="rounded-full border border-white/10 px-4 py-2 text-xs text-mist/80 transition hover:border-glow/50 hover:text-white"
                >
                  {prompt}
                </button>
              ))}
            </div>
          </div>
        </section>

        <section className="flex min-h-[600px] w-full flex-1 flex-col rounded-3xl border border-white/10 bg-white/5 shadow-panel">
          <header className="flex flex-wrap items-center justify-between gap-3 border-b border-white/10 px-6 py-4">
            <div>
              <p className="text-xs uppercase tracking-[0.3em] text-glow/70">Chat</p>
              <h2 className="font-display text-xl text-white">
                {activeAgent?.label || "Agent"}
              </h2>
            </div>
            <div className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-mist/70">
              {activeAgent?.description}
            </div>
          </header>

          <div
            ref={listRef}
            className="flex-1 space-y-4 overflow-y-auto px-6 py-6"
          >
            {messages.map((message) => (
              <div
                key={message.id}
                className={`flex ${
                  message.role === "user" ? "justify-end" : "justify-start"
                }`}
              >
                <div
                  className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-relaxed shadow-float ${
                    message.role === "user"
                      ? "bg-tide text-white"
                      : "bg-white/10 text-mist"
                  }`}
                >
                  <p className="whitespace-pre-wrap">{message.content}</p>
                  {message.meta?.type === "qa" && message.meta.sources?.length ? (
                    <div className="mt-3 space-y-1 border-t border-white/10 pt-3 text-xs text-glow/80">
                      <p className="font-semibold">Nguồn tham khảo</p>
                      {message.meta.sources.map((source, idx) => (
                        <div key={`${source}-${idx}`} className="truncate">
                          {source}
                        </div>
                      ))}
                    </div>
                  ) : null}
                  {message.meta?.type === "orchestration" && message.meta.details?.length ? (
                    <div className="mt-3 space-y-1 border-t border-white/10 pt-3 text-xs text-glow/80">
                      {message.meta.details.map((detail) => (
                        <div key={detail}>{detail}</div>
                      ))}
                    </div>
                  ) : null}
                  {message.meta?.type === "orchestration" && message.meta.delegated?.length ? (
                    <div className="mt-3 space-y-2 border-t border-white/10 pt-3 text-xs text-mist/80">
                      <p className="font-semibold text-glow/80">Kết quả delegate</p>
                      {message.meta.delegated.map((item, idx) => (
                        <div key={`${item.agent}-${idx}`} className="rounded-xl bg-white/5 px-3 py-2">
                          <div className="font-semibold text-white/80">
                            {item.agent}
                          </div>
                          <div className="mt-1 whitespace-pre-wrap">{item.answer}</div>
                          {item.error ? (
                            <div className="mt-1 text-ember">Error: {item.error}</div>
                          ) : null}
                        </div>
                      ))}
                    </div>
                  ) : null}
                </div>
              </div>
            ))}
            {loading ? (
              <div className="flex justify-start">
                <div className="rounded-2xl bg-white/10 px-4 py-3 text-sm text-mist">
                  Đang xử lý...
                </div>
              </div>
            ) : null}
          </div>

          <form onSubmit={onSubmit} className="border-t border-white/10 p-4">
            <div className="flex flex-col gap-3 md:flex-row md:items-end">
              <div className="flex-1">
                <label className="block text-xs uppercase tracking-[0.3em] text-glow/70">
                  Tin nhắn
                </label>
                <textarea
                  value={input}
                  onChange={(event) => setInput(event.target.value)}
                  onKeyDown={onKeyDown}
                  rows={3}
                  placeholder="Nhập câu hỏi của bạn..."
                  className="mt-2 w-full resize-none rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-white outline-none focus:border-glow/60"
                />
              </div>
              <button
                type="submit"
                disabled={loading}
                className="rounded-2xl bg-ember px-6 py-3 text-sm font-semibold text-ink transition hover:bg-[#ffd28c] disabled:cursor-not-allowed disabled:opacity-70"
              >
                Gửi
              </button>
            </div>
            {error ? (
              <p className="mt-3 text-xs text-ember">{error}</p>
            ) : null}
          </form>
        </section>
      </div>
    </div>
  );
}
