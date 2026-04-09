import React, { useEffect, useMemo, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

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

function getSourceHref(source) {
  if (typeof source !== "string") return "";
  const trimmed = source.trim();
  if (!trimmed) return "";
  return /^https?:\/\//i.test(trimmed) ? trimmed : "";
}

function toDisplayText(value) {
  if (typeof value === "string") return value;
  if (value === null || value === undefined) return "";
  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }

  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

export default function App() {
  const [agent, setAgent] = useState("orchestration");
  const [conversationId, setConversationId] = useState("default");
  const [userName, setUserName] = useState("Nguyen Van A");
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

  const createNewChat = () => {
    if (!activeAgent) return;
    const newConversationId = `chat-${Date.now()}`;
    setConversationId(newConversationId);
    setMessages([
      buildAgentIntro(activeAgent.id, activeAgent.label, activeAgent.description)
    ]);
    setInput("");
    setError("");
    setLoading(false);
    scrollToBottom();
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-800">
      <div className="mx-auto flex min-h-screen w-full max-w-[1400px] flex-col gap-4 p-3 md:p-4 lg:flex-row">
        <aside className="w-full rounded-3xl border border-sky-100 bg-white/90 p-4 shadow-panel backdrop-blur-sm lg:w-[320px] lg:p-5">
          <div className="rounded-2xl bg-gradient-to-r from-sky-600 to-cyan-500 p-4 text-white">
            <p className="font-display text-xs uppercase tracking-[0.22em] text-white/80">
              Vinuni Health
            </p>
            <h1 className="mt-2 font-display text-xl font-semibold leading-tight">
              Medical Assistant
            </h1>
            <p className="mt-2 text-sm text-cyan-50/90">
              Hỗ trợ hỏi đáp bệnh lý, tra cứu thuốc và đặt lịch khám.
            </p>
          </div>

          <div className="mt-4 space-y-4">
            <button
              type="button"
              onClick={createNewChat}
              className="w-full rounded-2xl bg-sky-600 px-4 py-3 text-sm font-semibold text-white transition hover:bg-sky-700"
            >
              + Tạo chat mới
            </button>

            <div className="rounded-2xl border border-sky-100 bg-sky-50/60 p-4">
              <h2 className="font-display text-sm font-semibold text-slate-800">
                User Settings
              </h2>
              <div className="mt-3 space-y-3">
                <div>
                  <label className="block text-xs uppercase tracking-[0.16em] text-slate-500">
                    Tên hiển thị
                  </label>
                  <input
                    value={userName}
                    onChange={(event) => setUserName(event.target.value)}
                    className="mt-2 w-full rounded-xl border border-sky-100 bg-white px-3 py-2 text-sm text-slate-700 outline-none transition focus:border-sky-400"
                    placeholder="Nguyen Van A"
                  />
                </div>

                <div>
                  <label className="block text-xs uppercase tracking-[0.16em] text-slate-500" htmlFor="conversationId">
                    Conversation ID
                  </label>
                  <input
                    id="conversationId"
                    value={conversationId}
                    onChange={(event) => setConversationId(event.target.value)}
                    className="mt-2 w-full rounded-xl border border-sky-100 bg-white px-3 py-2 text-sm text-slate-700 outline-none transition focus:border-sky-400"
                    placeholder="default"
                  />
                </div>
              </div>
            </div>

            <div className="rounded-2xl border border-sky-100 bg-white p-4">
              <h3 className="font-display text-sm font-semibold text-slate-800">
                Gợi ý nhanh
              </h3>
              <div className="mt-3 flex flex-wrap gap-2">
                {QUICK_PROMPTS.map((prompt) => (
                  <button
                    key={prompt}
                    type="button"
                    onClick={() => sendMessage(prompt)}
                    className="rounded-full border border-sky-200 bg-sky-50 px-3 py-2 text-xs text-sky-700 transition hover:border-sky-400 hover:bg-sky-100"
                  >
                    {prompt}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </aside>

        <section className="flex h-[calc(100vh-1.5rem)] min-h-0 w-full flex-1 flex-col overflow-hidden rounded-3xl border border-sky-100 bg-white/90 shadow-panel backdrop-blur-sm md:h-[calc(100vh-2rem)]">
          <header className="border-b border-sky-100 bg-white px-4 py-4 md:px-6">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="text-xs uppercase tracking-[0.2em] text-slate-500">Phòng khám trực tuyến</p>
                <h2 className="font-display text-xl font-semibold text-slate-800">
                  Xin chào, {userName || "bạn"}
                </h2>
              </div>
              <div className="rounded-full border border-sky-200 bg-sky-50 px-3 py-1 text-xs text-sky-700">
                API: {API_BASE}
              </div>
            </div>

            <div className="mt-4 flex flex-wrap gap-2">
              {AGENTS.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => setAgent(item.id)}
                  className={`rounded-xl border px-4 py-2 text-sm font-medium transition ${
                    agent === item.id
                      ? "border-sky-600 bg-sky-600 text-white"
                      : "border-sky-200 bg-sky-50 text-sky-700 hover:border-sky-400 hover:bg-sky-100"
                  }`}
                >
                  {item.label}
                </button>
              ))}
            </div>

            <p className="mt-3 text-sm text-slate-600">
              {activeAgent?.description}
            </p>
          </header>

          <div
            ref={listRef}
            className="min-h-0 flex-1 space-y-4 overflow-y-auto bg-gradient-to-b from-white to-sky-50/70 px-4 py-5 md:px-6"
          >
            {messages.map((message) => (
              <div
                key={message.id}
                className={`flex ${
                  message.role === "user" ? "justify-end" : "justify-start"
                }`}
              >
                <div
                  className={`max-w-[88%] rounded-2xl border px-5 py-4 text-base leading-7 shadow-float md:max-w-[80%] ${
                    message.role === "user"
                      ? "border-sky-600 bg-sky-600 text-white"
                      : "border-sky-100 bg-white text-slate-700"
                  }`}
                >
                  {message.role === "assistant" ? (
                    <div className="markdown-content">
                      <ReactMarkdown
                        remarkPlugins={[remarkGfm]}
                        components={{
                          a: ({ ...props }) => (
                            <a
                              {...props}
                              target="_blank"
                              rel="noreferrer"
                              className="underline decoration-sky-400 underline-offset-2 hover:text-sky-900"
                            />
                          )
                        }}
                      >
                        {toDisplayText(message.content)}
                      </ReactMarkdown>
                    </div>
                  ) : (
                    <p className="whitespace-pre-wrap">{toDisplayText(message.content)}</p>
                  )}

                  {message.meta?.type === "qa" && message.meta.sources?.length ? (
                    <div className="mt-3 space-y-1 border-t border-sky-100 pt-3 text-xs text-sky-700">
                      <p className="font-semibold">Nguồn tham khảo</p>
                      {message.meta.sources.map((source, idx) => {
                        const sourceText = toDisplayText(source);
                        const href = getSourceHref(sourceText);
                        return (
                          <div key={`source-${idx}`} className="truncate">
                            {href ? (
                              <a
                                href={href}
                                target="_blank"
                                rel="noreferrer"
                                className="underline decoration-sky-400 underline-offset-2 hover:text-sky-900"
                              >
                                {sourceText}
                              </a>
                            ) : (
                              <span>{sourceText}</span>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  ) : null}

                  {message.meta?.type === "orchestration" && message.meta.details?.length ? (
                    <div className="mt-3 space-y-1 border-t border-sky-100 pt-3 text-xs text-sky-700">
                      {message.meta.details.map((detail) => (
                        <div key={detail}>{detail}</div>
                      ))}
                    </div>
                  ) : null}

                </div>
              </div>
            ))}

            {loading ? (
              <div className="flex justify-start">
                <div className="rounded-2xl border border-sky-100 bg-white px-4 py-3 text-sm text-slate-600">
                  Đang xử lý...
                </div>
              </div>
            ) : null}
          </div>

          <form onSubmit={onSubmit} className="border-t border-sky-100 bg-white p-4 md:p-5">
            <div className="flex flex-col gap-3 md:flex-row md:items-end">
              <div className="flex-1">
                <label className="block text-xs uppercase tracking-[0.2em] text-slate-500">
                  Tin nhắn
                </label>
                <textarea
                  value={input}
                  onChange={(event) => setInput(event.target.value)}
                  onKeyDown={onKeyDown}
                  rows={4}
                  placeholder="Nhập câu hỏi của bạn..."
                  className="mt-2 w-full resize-none rounded-2xl border border-sky-200 bg-slate-50 px-4 py-3 text-base leading-7 text-slate-700 outline-none transition focus:border-sky-500"
                />
              </div>
              <button
                type="submit"
                disabled={loading}
                className="rounded-2xl bg-sky-600 px-6 py-3 text-sm font-semibold text-white transition hover:bg-sky-700 disabled:cursor-not-allowed disabled:opacity-70"
              >
                Gửi
              </button>
            </div>

            {error ? (
              <p className="mt-3 text-xs text-red-600">{error}</p>
            ) : null}
          </form>
        </section>
      </div>
    </div>
  );
}
