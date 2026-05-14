import { useState } from 'react';
import { GlassCard } from '@/components/common/GlassCard';
import { LegalCitationCard } from '@/components/common/LegalCitationCard';
import { LoadingSpinner } from '@/components/common/LoadingSpinner';
import { TranscriptBubble } from '@/components/common/TranscriptBubble';
import { TabSwitcher } from '@/components/common/TabSwitcher';
import { challengeArgument } from '@/services/legalApi';
import { getApiError } from '@/services/api';
import { useToast } from '@/contexts/ToastContext';
import { formatShortDate, safeString } from '@/utils/format';

const tabs = ['Response', 'Citations', 'Questions'];

export function ChallengePage() {
  const { notify } = useToast();
  const [premise, setPremise] = useState('');
  const [argument, setArgument] = useState('');
  const [sessionId, setSessionId] = useState('');
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState(tabs[0]);
  const [response, setResponse] = useState<{ opposing_response?: string; statutory_citations?: string[]; socratic_questions?: string[]; metadata?: Record<string, unknown> } | null>(null);

  const handleChallenge = async () => {
    if (!premise.trim() || !argument.trim()) {
      notify({ variant: 'info', title: 'Inputs required', message: 'Provide both a premise and an argument.' });
      return;
    }

    setLoading(true);
    try {
      const result = await challengeArgument({ premise: premise.trim(), userArgument: argument.trim(), sessionId: sessionId.trim() || undefined });
      setResponse(result);
      setActiveTab('Response');
      notify({ variant: 'success', title: 'Challenge complete', message: 'Opposing counsel response generated.' });
    } catch (error) {
      notify({ variant: 'error', title: 'Challenge failed', message: getApiError(error).message });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6 p-6">
      <GlassCard title="Challenge my argument" subtitle="Pressure-test a premise and your courtroom position">
        <div className="grid gap-4 xl:grid-cols-[1fr_1fr]">
          <label className="block text-sm text-slate-700">
            <span className="mb-2 block text-xs uppercase tracking-[0.3em] text-slate-500">Premise</span>
            <textarea
              value={premise}
              onChange={(event) => setPremise(event.target.value)}
              rows={10}
              className="min-h-[260px] w-full rounded-2xl border border-amber-200/70 bg-white px-4 py-3 text-sm text-slate-900 placeholder:text-slate-500 focus:border-electric/40 focus:outline-none"
              placeholder="Enter the factual scenario or legal issue to challenge."
            />
          </label>
          <label className="block text-sm text-slate-700">
            <span className="mb-2 block text-xs uppercase tracking-[0.3em] text-slate-500">Argument</span>
            <textarea
              value={argument}
              onChange={(event) => setArgument(event.target.value)}
              rows={10}
              className="min-h-[260px] w-full rounded-2xl border border-amber-200/70 bg-white px-4 py-3 text-sm text-slate-900 placeholder:text-slate-500 focus:border-electric/40 focus:outline-none"
              placeholder="Write the argument that opposing counsel should attack."
            />
          </label>
        </div>

        <div className="mt-4 grid gap-3 md:grid-cols-[1fr_auto]">
          <input
            value={sessionId}
            onChange={(event) => setSessionId(event.target.value)}
            placeholder="Optional session id"
            className="rounded-2xl border border-amber-200/70 bg-white px-4 py-3 text-sm text-slate-900 placeholder:text-slate-500 focus:border-electric/40 focus:outline-none"
          />
          <button
            type="button"
            onClick={handleChallenge}
            disabled={loading}
            className="rounded-full bg-gradient-to-r from-electric to-emeraldGlow px-6 py-3 text-sm font-semibold text-white transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {loading ? 'Generating...' : 'Challenge Argument'}
          </button>
        </div>
      </GlassCard>

      <div className="grid gap-4 xl:grid-cols-[1fr_0.9fr]">
        <GlassCard title="Transcript" subtitle="Courtroom-style response format">
          {loading ? (
            <LoadingSpinner label="Generating opposing counsel response" />
          ) : response ? (
            <div className="space-y-4">
              <TranscriptBubble speaker="Opposing Counsel" tone="emerald" content={safeString(response.opposing_response, 'No response returned.')} />
              <TranscriptBubble speaker="Student Advocate" tone="electric" content={argument || 'Your argument will appear here.'} />
              <p className="text-xs uppercase tracking-[0.3em] text-slate-500">Generated at {formatShortDate(new Date())}</p>
            </div>
          ) : (
            <p className="text-sm text-slate-600">Enter a premise and an argument to generate a challenge.</p>
          )}
        </GlassCard>

        <GlassCard title="AI analysis" subtitle="Switch through the response, citations, and questions">
          <TabSwitcher tabs={tabs} active={activeTab} onChange={setActiveTab} />
          <div className="mt-5 space-y-4">
            {activeTab === 'Response' ? <p className="text-sm leading-7 text-slate-700">{response ? safeString(response.opposing_response, 'No response returned.') : 'No response yet.'}</p> : null}
            {activeTab === 'Citations' ? <LegalCitationCard title="Statutory citation section" citations={response?.statutory_citations ?? []} tone="gold" /> : null}
            {activeTab === 'Questions' ? (
              <div className="space-y-3">
                {(response?.socratic_questions ?? []).length ? (response?.socratic_questions ?? []).map((question) => (
                  <div key={question} className="rounded-2xl border border-amber-200/70 bg-white p-4 text-sm leading-7 text-slate-700">
                    {question}
                  </div>
                )) : <p className="text-sm text-slate-600">Socratic questions will appear after the backend responds.</p>}
              </div>
            ) : null}
          </div>
        </GlassCard>
      </div>
    </div>
  );
}
