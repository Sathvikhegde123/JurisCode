import { useEffect, useMemo, useState } from 'react';
import { EmptyState } from '@/components/common/EmptyState';
import { GlassCard } from '@/components/common/GlassCard';
import { LoadingSpinner } from '@/components/common/LoadingSpinner';
import { ScoreMeter } from '@/components/common/ScoreMeter';
import { TabSwitcher } from '@/components/common/TabSwitcher';
import { TopicBadge } from '@/components/common/TopicBadge';
import { TranscriptBubble } from '@/components/common/TranscriptBubble';
import { getApiError, loadSessionSummaries } from '@/services/api';
import { getPremiseModes, getPremiseTopics, startPractice, submitPracticeArgument } from '@/services/legalApi';
import { useToast } from '@/contexts/ToastContext';
import { clamp, formatShortDate, safeNumber, safeString } from '@/utils/format';

type PracticeFeedback = {
  summary: string;
  suggestions: string[];
  objections: string[];
  evidentiary_gaps: string[];
  procedural_issues: string[];
  burden_of_proof_issues: string[];
  contradictions: string[];
  improvement_suggestions: string[];
  argument_strength_score: number;
};

const defaultTabs = ['Opposing Counsel', 'Feedback', 'Suggestions', 'Score'];

function readText(record: Record<string, unknown>, keys: string[], fallback = '') {
  for (const key of keys) {
    const value = record[key];
    if (typeof value === 'string' && value.trim()) {
      return value;
    }
  }

  return fallback;
}

function readList(record: Record<string, unknown>, keys: string[]) {
  for (const key of keys) {
    const value = record[key];
    if (Array.isArray(value)) {
      return value.filter((item): item is string => typeof item === 'string' && item.trim().length > 0);
    }
  }

  return [] as string[];
}

function mapFeedback(raw: unknown): PracticeFeedback {
  const record = (raw && typeof raw === 'object' && !Array.isArray(raw) ? raw : {}) as Record<string, unknown>;
  const nested = (record.objection_feedback && typeof record.objection_feedback === 'object' && !Array.isArray(record.objection_feedback)
    ? (record.objection_feedback as Record<string, unknown>)
    : record) as Record<string, unknown>;

  return {
    summary: readText(nested, ['summary', 'courtroom_feedback', 'feedback'], 'Your argument has been recorded and scored.'),
    suggestions: readList(nested, ['suggestions', 'improvement_suggestions']),
    objections: readList(nested, ['objections']),
    evidentiary_gaps: readList(nested, ['evidentiary_gaps', 'missing_facts_or_evidence']),
    procedural_issues: readList(nested, ['procedural_issues']),
    burden_of_proof_issues: readList(nested, ['burden_of_proof_issues']),
    contradictions: readList(nested, ['contradictions']),
    improvement_suggestions: readList(nested, ['improvement_suggestions', 'suggestions']),
    argument_strength_score: clamp(safeNumber(nested.argument_strength_score ?? record.score, 62), 0, 100),
  };
}

export function PracticeArenaPage() {
  const { notify } = useToast();
  const [topics, setTopics] = useState<string[]>([]);
  const [modes, setModes] = useState<string[]>([]);
  const [loadingMeta, setLoadingMeta] = useState(true);
  const [starting, setStarting] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [activeTab, setActiveTab] = useState(defaultTabs[0]);
  const [selectedTopic, setSelectedTopic] = useState('');
  const [selectedMode, setSelectedMode] = useState('');
  const [randomize, setRandomize] = useState(true);
  const [premise, setPremise] = useState('Start a practice session to generate a courtroom premise.');
  const [sessionId, setSessionId] = useState('');
  const [argument, setArgument] = useState('');
  const [typedOpposing, setTypedOpposing] = useState('');
  const [responsePayload, setResponsePayload] = useState<Record<string, unknown> | null>(null);
  const [feedback, setFeedback] = useState<PracticeFeedback>({
    summary: 'No feedback yet. Start a session and submit your argument.',
    suggestions: [],
    objections: [],
    evidentiary_gaps: [],
    procedural_issues: [],
    burden_of_proof_issues: [],
    contradictions: [],
    improvement_suggestions: [],
    argument_strength_score: 0,
  });
  const [history, setHistory] = useState(loadSessionSummaries());

  useEffect(() => {
    Promise.all([getPremiseTopics(), getPremiseModes()])
      .then(([loadedTopics, loadedModes]) => {
        setTopics(loadedTopics);
        setModes(loadedModes);
        setSelectedTopic(loadedTopics[0] ?? '');
        setSelectedMode(loadedModes[0] ?? '');
      })
      .catch((error) => {
        notify({ variant: 'error', title: 'Could not load practice options', message: getApiError(error).message });
      })
      .finally(() => setLoadingMeta(false));
  }, [notify]);

  useEffect(() => {
    const source = safeString((responsePayload ?? {})['opposing_response'], '');
    if (!source) {
      setTypedOpposing('');
      return;
    }

    let index = 0;
    setTypedOpposing('');
    const timer = window.setInterval(() => {
      index += 1;
      setTypedOpposing(source.slice(0, index));
      if (index >= source.length) {
        window.clearInterval(timer);
      }
    }, 12);

    return () => window.clearInterval(timer);
  }, [responsePayload]);

  const visibleTabs = useMemo(() => defaultTabs, []);

  const currentResponse = responsePayload ?? {};

  const handleStartPractice = async () => {
    setStarting(true);
    try {
      const started = await startPractice({ topic: selectedTopic, mode: selectedMode, randomize });
      setSessionId(started.session_id ?? '');
      setPremise(started.premise ?? 'Your premise will appear here.');
      setArgument('');
      setResponsePayload(null);
      setFeedback((current) => ({ ...current, summary: 'Practice session started. Submit your first argument.' }));
      setHistory(loadSessionSummaries());
      notify({ variant: 'success', title: 'Practice started', message: `Session ${started.session_id ?? 'created'} is ready.` });
    } catch (error) {
      notify({ variant: 'error', title: 'Could not start practice', message: getApiError(error).message });
    } finally {
      setStarting(false);
    }
  };

  const handleSubmitArgument = async () => {
    if (!sessionId) {
      notify({ variant: 'info', title: 'Start a session first', message: 'Generate a premise before submitting your argument.' });
      return;
    }

    if (!argument.trim()) {
      notify({ variant: 'info', title: 'Argument required', message: 'Write a courtroom argument before submitting.' });
      return;
    }

    setSubmitting(true);
    try {
      const result = await submitPracticeArgument({ sessionId, userArgument: argument.trim() });
      const mappedFeedback = mapFeedback(result);
      setResponsePayload(result as Record<string, unknown>);
      setFeedback(mappedFeedback);
      setHistory(loadSessionSummaries());
      setActiveTab('Opposing Counsel');
      notify({ variant: 'success', title: 'Argument analyzed', message: `Strength score ${mappedFeedback.argument_strength_score}.` });
    } catch (error) {
      notify({ variant: 'error', title: 'Submission failed', message: getApiError(error).message });
    } finally {
      setSubmitting(false);
    }
  };

  const suggestionsList = feedback.improvement_suggestions.length ? feedback.improvement_suggestions : feedback.suggestions;
  const score = feedback.argument_strength_score || safeNumber(currentResponse.score, 0);

  return (
    <div className="space-y-6">
      <section className="grid gap-4 xl:grid-cols-[1fr_1.1fr_0.9fr]">
        <GlassCard title="Session premise" subtitle="Start the courtroom simulation here">
          <div className="space-y-4">
            <div className="flex flex-wrap gap-2">
              <TopicBadge label={selectedTopic || 'No topic selected'} active />
              <TopicBadge label={selectedMode || 'No mode selected'} />
              <TopicBadge label={randomize ? 'Randomized' : 'Fixed'} />
            </div>
            <p className="court-text text-sm">{premise}</p>
            <div className="rounded-2xl border border-amber-200/70 bg-white p-4 text-sm text-slate-700">
              <p className="text-xs uppercase tracking-[0.3em] text-slate-500">Session</p>
              <p className="mt-2">{sessionId ? `ID ${sessionId}` : 'No active session yet.'}</p>
              <p className="mt-1">{history[0] ? `Last saved ${formatShortDate(history[0].createdAt)}` : 'Practice history will appear here.'}</p>
            </div>
          </div>
        </GlassCard>

        <GlassCard title="Your argument" subtitle="Write in advocate style, then submit for analysis">
          <div className="space-y-4">
            <label className="block text-sm text-slate-700">
              <span className="mb-2 block text-xs uppercase tracking-[0.3em] text-slate-500">Argument</span>
              <textarea
                value={argument}
                onChange={(event) => setArgument(event.target.value)}
                rows={12}
                className="min-h-[280px] w-full rounded-2xl border border-amber-200/70 bg-white px-4 py-3 text-sm text-slate-900 placeholder:text-slate-500 focus:border-electric/40 focus:outline-none"
                placeholder="Frame the issue, state the governing rule, and support your position with reasons."
              />
            </label>
            <div className="flex flex-wrap items-center gap-3">
              <button
                type="button"
                onClick={handleStartPractice}
                disabled={starting || loadingMeta}
                className="rounded-full bg-gradient-to-r from-electric to-emeraldGlow px-5 py-3 text-sm font-semibold text-white transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {starting ? 'Starting...' : 'Start Practice'}
              </button>
              <button
                type="button"
                onClick={handleSubmitArgument}
                disabled={submitting || !sessionId}
                className="rounded-full border border-amber-200/80 bg-white px-5 py-3 text-sm font-semibold text-slate-900 transition hover:border-electric/40 hover:bg-amber-100/70 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {submitting ? 'Submitting...' : 'Submit Argument'}
              </button>
              <label className="flex items-center gap-2 rounded-full border border-amber-200/70 bg-white px-4 py-2 text-sm text-slate-700">
                <input type="checkbox" checked={randomize} onChange={(event) => setRandomize(event.target.checked)} className="accent-electric" />
                Randomize premise
              </label>
            </div>
          </div>
        </GlassCard>

        <GlassCard title="Practice controls" subtitle="Select a topic and mode before you begin">
          {loadingMeta ? (
            <LoadingSpinner label="Loading topics and modes" />
          ) : (
            <div className="space-y-5">
              <div>
                <p className="section-kicker">Topics</p>
                <div className="mt-3 flex flex-wrap gap-2">
                  {topics.length ? topics.map((topic) => (
                    <button key={topic} type="button" onClick={() => setSelectedTopic(topic)} className="rounded-full">
                      <TopicBadge label={topic} active={selectedTopic === topic} />
                    </button>
                  )) : <EmptyState title="No topics returned" description="The backend did not return any curated topics yet." />}
                </div>
              </div>
              <div>
                <p className="section-kicker">Modes</p>
                <div className="mt-3 flex flex-wrap gap-2">
                  {modes.length ? modes.map((mode) => (
                    <button key={mode} type="button" onClick={() => setSelectedMode(mode)} className="rounded-full">
                      <TopicBadge label={mode} active={selectedMode === mode} />
                    </button>
                  )) : <p className="text-sm text-slate-600">No mode data returned.</p>}
                </div>
              </div>
            </div>
          )}
        </GlassCard>
      </section>

      <section className="grid gap-4 xl:grid-cols-[1.15fr_0.85fr]">
        <GlassCard className="min-h-[540px]" title="Courtroom transcript" subtitle="Live adversarial feedback and scoring">
          <div className="space-y-5">
            <TranscriptBubble speaker="Judge" tone="gold" content="State the issue clearly, counsel, and do not skip the legal basis." />
            <TranscriptBubble speaker="Student Advocate" tone="electric" content={argument.trim() || 'Your argument transcript will appear here after submission.'} />
            <TranscriptBubble speaker="AI Opposing Counsel" tone="emerald" content={typedOpposing || 'The opposing counsel response will render here after the backend responds.'} />
          </div>
        </GlassCard>

        <GlassCard className="min-h-[540px]" title="Analysis panel" subtitle="Switch between the major feedback views">
          <TabSwitcher tabs={visibleTabs} active={activeTab} onChange={setActiveTab} />
          <div className="mt-5 space-y-4">
            {activeTab === 'Opposing Counsel' ? (
              <div className="space-y-3">
                <p className="text-sm text-slate-700">{safeString(currentResponse.opposing_response, 'No opposing counsel response yet.') || 'No opposing counsel response yet.'}</p>
                <ScoreMeter score={score} label="Response pressure" />
              </div>
            ) : null}

            {activeTab === 'Feedback' ? (
              <div className="space-y-3">
                <p className="text-sm leading-7 text-slate-700">{feedback.summary}</p>
                <div className="grid gap-3 sm:grid-cols-2">
                  <div className="rounded-2xl border border-amber-200/70 bg-white p-4">
                    <p className="text-xs uppercase tracking-[0.3em] text-slate-500">Objections</p>
                    <p className="mt-2 text-sm text-slate-700">{feedback.objections.length ? feedback.objections.join('; ') : 'No objection summary returned.'}</p>
                  </div>
                  <div className="rounded-2xl border border-amber-200/70 bg-white p-4">
                    <p className="text-xs uppercase tracking-[0.3em] text-slate-500">Weaknesses</p>
                    <p className="mt-2 text-sm text-slate-700">{feedback.contradictions.length ? feedback.contradictions.join('; ') : 'No contradictions detected.'}</p>
                  </div>
                </div>
              </div>
            ) : null}

            {activeTab === 'Suggestions' ? (
              <div className="space-y-3">
                {suggestionsList.length ? suggestionsList.map((suggestion) => (
                  <div key={suggestion} className="rounded-2xl border border-amber-200/70 bg-white p-4 text-sm leading-7 text-slate-700">
                    {suggestion}
                  </div>
                )) : <p className="text-sm text-slate-600">Submit an argument to receive targeted improvements.</p>}
              </div>
            ) : null}

            {activeTab === 'Score' ? (
              <div className="space-y-4">
                <ScoreMeter score={score} />
                <div className="grid gap-3 sm:grid-cols-2">
                  <div className="rounded-2xl border border-amber-200/70 bg-white p-4 text-sm text-slate-700">
                    <p className="text-xs uppercase tracking-[0.3em] text-slate-500">Evidentiary gaps</p>
                    <p className="mt-2">{feedback.evidentiary_gaps.length ? feedback.evidentiary_gaps.join('; ') : 'None flagged.'}</p>
                  </div>
                  <div className="rounded-2xl border border-amber-200/70 bg-white p-4 text-sm text-slate-700">
                    <p className="text-xs uppercase tracking-[0.3em] text-slate-500">Procedure</p>
                    <p className="mt-2">{feedback.procedural_issues.length ? feedback.procedural_issues.join('; ') : 'No procedural issues returned.'}</p>
                  </div>
                </div>
              </div>
            ) : null}
          </div>
        </GlassCard>
      </section>
    </div>
  );
}
