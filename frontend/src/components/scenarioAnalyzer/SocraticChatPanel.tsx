import { LawyerWarningCard } from '@/components/scenarioAnalyzer/LawyerWarningCard';
import type { LawyerWarningShape } from '@/utils/scenarioReportMapping';
import { classNames } from '@/utils/classNames';
import { useEffect, useRef } from 'react';

export type ChatMessageVM = {
  role: 'user' | 'assistant';
  content: string;
  metadata?: {
    updated_understanding: string[];
    recommended_next_steps: string[];
    lawyer_warning: LawyerWarningShape;
  };
  created_at?: string;
};

type SocraticChatPanelProps = {
  messages: ChatMessageVM[];
  chatInput: string;
  onChatInputChange: (v: string) => void;
  onSend: () => void;
  chatLoading: boolean;
};

export function SocraticChatPanel({
  messages,
  chatInput,
  onChatInputChange,
  onSend,
  chatLoading,
}: SocraticChatPanelProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, chatLoading]);

  const canSend = chatInput.trim().length > 0 && !chatLoading;

  return (
    <div className="flex min-h-[min(420px,62vh)] flex-col rounded-3xl border border-amber-200/70 bg-white/95 shadow-sm">
      <div className="shrink-0 border-b border-amber-200/60 px-4 py-3">
        <p className="text-sm font-semibold text-slate-900">Guided follow-up</p>
        <p className="text-xs text-slate-600">One question at a time. Short answers work best.</p>
      </div>

      <div className="min-h-0 flex-1 space-y-3 overflow-y-auto px-4 py-4">
        {messages.map((m, idx) => (
          <div key={`${m.created_at ?? 'm'}-${idx}`} className={classNames('flex', m.role === 'user' ? 'justify-end' : 'justify-start')}>
            <div
              className={classNames(
                'max-w-[92%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed shadow-sm sm:max-w-[85%]',
                m.role === 'user'
                  ? 'rounded-br-md border border-electric/25 bg-electric/10 text-slate-900'
                  : 'rounded-bl-md border border-amber-200/70 bg-[#fffaf3] text-slate-800',
              )}
            >
              <p className="whitespace-pre-wrap">{m.content}</p>

              {m.role === 'assistant' && m.metadata && m.metadata.updated_understanding.length > 0 ? (
                <details className="mt-2 rounded-xl border border-amber-200/60 bg-white/80 px-3 py-2 text-xs text-slate-700">
                  <summary className="cursor-pointer font-medium text-slate-800">Updated understanding</summary>
                  <ul className="mt-2 list-disc space-y-1 pl-4">
                    {m.metadata.updated_understanding.map((u) => (
                      <li key={u}>{u}</li>
                    ))}
                  </ul>
                </details>
              ) : null}

              {m.role === 'assistant' && m.metadata && m.metadata.recommended_next_steps.length > 0 ? (
                <ul className="mt-2 list-disc space-y-1 border-t border-amber-200/40 pt-2 pl-4 text-xs text-slate-700">
                  {m.metadata.recommended_next_steps.slice(0, 2).map((s) => (
                    <li key={s}>{s}</li>
                  ))}
                </ul>
              ) : null}

              {m.role === 'assistant' && m.metadata && m.metadata.lawyer_warning.required ? (
                <div className="mt-2">
                  <LawyerWarningCard warning={m.metadata.lawyer_warning} />
                </div>
              ) : null}
            </div>
          </div>
        ))}

        {chatLoading ? (
          <div className="flex justify-start">
            <div className="rounded-2xl border border-amber-200/70 bg-[#fffaf3] px-4 py-2.5 text-sm text-slate-600">
              JurisCode is thinking…
            </div>
          </div>
        ) : null}
        <div ref={bottomRef} />
      </div>

      <div className="shrink-0 border-t border-amber-200/60 bg-[#fffaf3]/90 px-3 py-3">
        <form
          className="flex flex-col gap-2 sm:flex-row sm:items-end"
          onSubmit={(e) => {
            e.preventDefault();
            if (canSend) {
              onSend();
            }
          }}
        >
          <textarea
            value={chatInput}
            onChange={(e) => onChatInputChange(e.target.value)}
            rows={2}
            placeholder="Type your answer…"
            className="min-h-[48px] flex-1 resize-none rounded-2xl border border-amber-200/80 bg-white px-3 py-2 text-sm outline-none focus:border-electric/50"
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                if (canSend) {
                  onSend();
                }
              }
            }}
          />
          <button
            type="submit"
            disabled={!canSend}
            className="shrink-0 rounded-full bg-electric px-6 py-2.5 text-sm font-semibold text-white transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-50"
          >
            Send
          </button>
        </form>
      </div>
    </div>
  );
}
