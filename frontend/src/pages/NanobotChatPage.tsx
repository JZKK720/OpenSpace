import { useCallback, useEffect, useRef, useState } from 'react';
import { externalAgentsApi } from '../api';
import { useI18n } from '../i18n';

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
}

type ChatStatus = 'idle' | 'sending' | 'error';

let _msgCounter = 0;
function nextId(): string {
  return String(++_msgCounter);
}

export default function NanobotChatPage() {
  const { t } = useI18n();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [threadId, setThreadId] = useState<string | null>(null);
  const [input, setInput] = useState('');
  const [status, setStatus] = useState<ChatStatus>('idle');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-scroll to bottom whenever messages change
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, status]);

  const handleNewConversation = useCallback(() => {
    setMessages([]);
    setThreadId(null);
    setInput('');
    setStatus('idle');
    setErrorMsg(null);
    textareaRef.current?.focus();
  }, []);

  const handleSend = useCallback(async () => {
    const trimmed = input.trim();
    if (!trimmed || status === 'sending') {
      return;
    }

    const userMsg: ChatMessage = { id: nextId(), role: 'user', content: trimmed };
    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setStatus('sending');
    setErrorMsg(null);

    try {
      const result = await externalAgentsApi.handoffToAgent('nanobot', {
        prompt: trimmed,
        threadId: threadId ?? undefined,
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC',
      });

      if (result.threadId) {
        setThreadId(result.threadId);
      }

      const responseText =
        result.latestTurn?.response?.trim() ||
        (result.turns?.length
          ? result.turns[result.turns.length - 1]?.response?.trim()
          : null);

      if (responseText) {
        const assistantMsg: ChatMessage = {
          id: nextId(),
          role: 'assistant',
          content: responseText,
        };
        setMessages((prev) => [...prev, assistantMsg]);
      }

      setStatus('idle');
    } catch (err) {
      const msg = err instanceof Error ? err.message : t('nanobot.status.error');
      setErrorMsg(msg);
      setStatus('error');
    }
  }, [input, status, threadId, t]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        void handleSend();
      }
    },
    [handleSend],
  );

  return (
    <div className="flex flex-col h-full max-w-4xl mx-auto px-4 py-6 gap-4">
      {/* Header */}
      <div className="flex items-center justify-between shrink-0">
        <div>
          <h1 className="text-2xl font-bold">{t('nanobot.title')}</h1>
          {threadId ? (
            <div className="text-xs text-muted mt-1 font-mono truncate max-w-[40ch]">
              {threadId}
            </div>
          ) : null}
        </div>
        <button
          type="button"
          className="btn-outline-ink text-sm shrink-0"
          onClick={handleNewConversation}
        >
          {t('nanobot.new_conversation')}
        </button>
      </div>

      {/* Message list */}
      <div className="flex-1 overflow-y-auto space-y-4 min-h-0">
        {messages.length === 0 && status === 'idle' ? (
          <div className="flex items-center justify-center h-full text-sm text-muted">
            {t('nanobot.placeholder')}
          </div>
        ) : null}

        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[75%] rounded-lg px-4 py-3 text-sm whitespace-pre-wrap break-words ${
                msg.role === 'user'
                  ? 'bg-primary text-white'
                  : 'bg-surface border border-[color:var(--color-border)]'
              }`}
            >
              {msg.content}
            </div>
          </div>
        ))}

        {status === 'sending' ? (
          <div className="flex justify-start">
            <div className="bg-surface border border-[color:var(--color-border)] rounded-lg px-4 py-3 text-sm text-muted">
              {t('nanobot.status.waiting')}
            </div>
          </div>
        ) : null}

        {status === 'error' && errorMsg ? (
          <div className="flex justify-start">
            <div className="bg-surface border border-[color:var(--color-border)] rounded-lg px-4 py-3 text-sm text-danger">
              {errorMsg}
            </div>
          </div>
        ) : null}

        <div ref={bottomRef} />
      </div>

      {/* Input bar */}
      <div className="shrink-0 flex gap-3 items-end">
        <textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={t('nanobot.placeholder')}
          rows={3}
          className="flex-1 p-3 field-surface resize-none"
          disabled={status === 'sending'}
        />
        <button
          type="button"
          className="btn-primary text-sm self-end"
          disabled={status === 'sending' || !input.trim()}
          onClick={() => { void handleSend(); }}
        >
          {t('nanobot.send')}
        </button>
      </div>
    </div>
  );
}
