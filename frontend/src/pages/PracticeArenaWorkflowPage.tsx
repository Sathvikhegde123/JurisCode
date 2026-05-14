import { useEffect, useMemo, useState, type ReactNode } from 'react';
import { GlassCard } from '@/components/common/GlassCard';
import { LoadingSpinner } from '@/components/common/LoadingSpinner';
import { ScoreMeter } from '@/components/common/ScoreMeter';
import { useToast } from '@/contexts/ToastContext';
import { getApiError } from '@/services/api';
import {
  createPracticeSession,
  generateJudgeEvaluation,
  generateOpposingCounselResponse,
  generatePracticePremise,
  getPremiseModes,
  getPremiseTopics,
  submitOpeningArgument,
  submitRebuttalArgument,
} from '@/services/legalApi';
import type {
  PracticeJudgeEvaluationResponse,
  PracticeOpposingResponse,
  PracticePremiseResponse,
  PracticeWorkflowArgumentResponse,
} from '@/types';
import { classNames } from '@/utils/classNames';
import { clamp, formatDateTime, formatNumber, formatPercent, safeNumber, safeString } from '@/utils/format';

type SessionStatus = 'active' | 'awaiting-opening' | 'opposing-response' | 'rebuttal' | 'judgment-complete';

type WorkflowStep = {
  label: string;
  description: string;
};

const workflowSteps: WorkflowStep[] = [
  { label: 'Create Session', description: 'Open a new practice arena session.' },
  { label: 'Generate Premise', description: 'Lock the facts and legal issue.' },
  { label: 'Opening Argument', description: 'Submit the student advocate draft.' },
  { label: 'Opposing Counsel', description: 'Render the AI challenge response.' },
  { label: 'Rebuttal', description: 'Draft the follow-up response.' },
  { label: 'Judge Evaluation', description: 'Review the final assessment.' },
];

const statusToneClasses: Record<SessionStatus, string> = {
  active: 'border-electric/30 bg-electric/10 text-electric',
  'awaiting-opening': 'border-mutedGold/30 bg-mutedGold/10 text-mutedGold',
  'opposing-response': 'border-rose-400/30 bg-rose-500/10 text-rose-200',
  rebuttal: 'border-emeraldGlow/30 bg-emeraldGlow/10 text-emeraldGlow',
  'judgment-complete': 'border-mutedGold/40 bg-mutedGold/15 text-mutedGold',
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value);
}

function normalizeStatus(raw: unknown, fallback: SessionStatus): SessionStatus {
  const value = safeString(raw, fallback).toLowerCase();
  if (value.includes('awaiting-opening')) return 'awaiting-opening';
  if (value.includes('opposing')) return 'opposing-response';
  if (value.includes('rebuttal')) return 'rebuttal';
  if (value.includes('judge') || value.includes('complete')) return 'judgment-complete';
  if (value.includes('active') || value.includes('session-created')) return 'active';
  return fallback;
}

function formatPremise(payload: unknown) {
  if (typeof payload === 'string') {
    return payload;
  }

  if (!payload) {
    return '';
  }

  try {
    return JSON.stringify(payload, null, 2);
  } catch {
    return String(payload);
  }
}

function StatusBadge({ label, tone }: { label: string; tone: SessionStatus | 'neutral' }) {
  const className =
    tone === 'neutral'
      ? 'border-white/10 bg-white/5 text-slate-300'
      : statusToneClasses[tone];
  return (
    <span className={classNames('inline-flex items-center rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-[0.22em]', className)}>
      {label}
    </span>
  );
}

function MetricTile({ label, value, helper }: { label: string; value: string; helper?: string }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
      <p className="text-[11px] uppercase tracking-[0.28em] text-slate-500">{label}</p>
      <p className="mt-2 break-words text-sm font-semibold text-white">{value}</p>
      {helper ? <p className="mt-1 text-xs leading-6 text-slate-400">{helper}</p> : null}
    </div>
  );
}

function StageStepper({ activeIndex }: { activeIndex: number }) {
  return (
    <div className="rounded-3xl border border-white/10 bg-white/5 p-4 shadow-glow backdrop-blur-xl">
      <div className="grid gap-3 grid-cols-3 xl:grid-cols-6">
        {workflowSteps.map((step, index) => {
          const completed = index < activeIndex;
          const current = index === activeIndex;
          return (
            <div
              key={step.label}
              className={classNames(
                'rounded-2xl border p-4 transition',
                completed
                  ? 'border-emeraldGlow/30 bg-emeraldGlow/10'
                  : current
                    ? 'border-electric/40 bg-electric/15'
                    : 'border-white/10 bg-[#07111f]'
              )}
            >
              <div className="flex items-center justify-between gap-3">
                <span className={classNames('text-xs uppercase tracking-[0.26em]', completed ? 'text-emeraldGlow' : current ? 'text-electric' : 'text-slate-500')}>
                  Step {index + 1}
                </span>
                <span className={classNames('h-2.5 w-2.5 rounded-full', completed ? 'bg-emeraldGlow' : current ? 'bg-electric' : 'bg-slate-600')} aria-hidden="true" />
              </div>
              <p className="mt-3 text-sm font-semibold text-white">{step.label}</p>
              <p className="mt-1 text-xs leading-6 text-slate-400">{step.description}</p>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function CircularScoreMeter({ score, label }: { score: number; label: string }) {
  const value = clamp(score, 0, 100);
  const degrees = value * 3.6;
  return (
    <div className="rounded-3xl border border-white/10 bg-[#08111f] p-5">
      <div className="mb-4 flex items-center justify-between gap-3">
        <p className="text-xs uppercase tracking-[0.28em] text-slate-500">{label}</p>
        <p className="text-sm font-semibold text-white">{formatPercent(value)}</p>
      </div>
      <div className="flex items-center justify-center">
        <div
          className="relative flex h-32 w-32 items-center justify-center rounded-full"
          style={{ background: `conic-gradient(#f5c45b 0deg ${degrees}deg, rgba(255,255,255,0.08) ${degrees}deg 360deg)` }}
        >
          <div className="flex h-24 w-24 items-center justify-center rounded-full border border-white/10 bg-[#05101b] text-center">
            <div>
              <p className="text-3xl font-semibold text-white">{Math.round(value)}</p>
              <p className="text-[10px] uppercase tracking-[0.3em] text-slate-500">out of 100</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function EmptyPanel({ title, description }: { title: string; description: string }) {
  return (
    <div className="rounded-3xl border border-dashed border-white/10 bg-white/5 p-5 text-sm text-slate-400">
      <p className="text-sm font-semibold text-white">{title}</p>
      <p className="mt-2 leading-7">{description}</p>
    </div>
  );
}

function JudgeCard({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="rounded-3xl border border-white/10 bg-[#08111f] p-5 shadow-glow">
      <p className="text-xs uppercase tracking-[0.28em] text-slate-500">{title}</p>
      <div className="mt-4">{children}</div>
    </div>
  );
}

function ScoreRibbon({ score }: { score: number }) {
  const value = clamp(score, 0, 100);
  return (
    <div className="rounded-3xl border border-mutedGold/30 bg-gradient-to-r from-mutedGold/20 via-mutedGold/10 to-transparent p-5">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.28em] text-mutedGold">Final Score</p>
          <p className="mt-2 text-4xl font-semibold text-white">{Math.round(value)}</p>
        </div>
        <div className="text-sm text-slate-300">
          <p>Score out of 100</p>
          <p className="mt-1 text-xs uppercase tracking-[0.28em] text-slate-500">Session judgment complete</p>
        </div>
      </div>
    </div>
  );
}

export function PracticeArenaPage() {
  const { notify } = useToast();
  const [topics, setTopics] = useState<string[]>([]);
  const [modes, setModes] = useState<string[]>([]);
  const [loadingMeta, setLoadingMeta] = useState(true);
  const [selectedTopic, setSelectedTopic] = useState('');
  const [selectedMode, setSelectedMode] = useState('');
  const [randomize, setRandomize] = useState(true);

  const [sessionId, setSessionId] = useState('');
  const [workflowStage, setWorkflowStage] = useState('Create Session');
  const [sessionStatus, setSessionStatus] = useState<SessionStatus>('active');
  const [currentRound, setCurrentRound] = useState(0);

  const [premiseResponse, setPremiseResponse] = useState<PracticePremiseResponse | null>(null);
  const [openingArgument, setOpeningArgument] = useState('');
  const [openingResponse, setOpeningResponse] = useState<PracticeWorkflowArgumentResponse | null>(null);
  const [opposingResponse, setOpposingResponse] = useState<PracticeOpposingResponse | null>(null);
  const [typedOpposing, setTypedOpposing] = useState('');
  const [opposingTimestamp, setOpposingTimestamp] = useState('');
  const [rebuttalArgument, setRebuttalArgument] = useState('');
  const [rebuttalResponse, setRebuttalResponse] = useState<PracticeWorkflowArgumentResponse | null>(null);
  const [judgeEvaluation, setJudgeEvaluation] = useState<PracticeJudgeEvaluationResponse | null>(null);

  const [creatingSession, setCreatingSession] = useState(false);
  const [generatingPremise, setGeneratingPremise] = useState(false);
  const [submittingOpening, setSubmittingOpening] = useState(false);
  const [generatingOpposing, setGeneratingOpposing] = useState(false);
  const [submittingRebuttal, setSubmittingRebuttal] = useState(false);
  const [generatingJudge, setGeneratingJudge] = useState(false);

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
    const content = safeString(opposingResponse?.content, '');
    if (!content) {
      setTypedOpposing('');
      setOpposingTimestamp('');
      return;
    }
    let index = 0;
    setTypedOpposing('');
    const step = Math.max(1, Math.ceil(content.length / 120));
    const timer = window.setInterval(() => {
      index += step;
      setTypedOpposing(content.slice(0, index));
      if (index >= content.length) window.clearInterval(timer);
    }, 16);
    return () => window.clearInterval(timer);
  }, [opposingResponse]);

  const premiseText = useMemo(() => formatPremise(premiseResponse?.premise), [premiseResponse]);
  const lockedFacts = premiseResponse?.locked_facts ?? [];
  const premiseSessionId = safeString(premiseResponse?.session_id, sessionId || 'Pending');
  const premiseStage = safeString(premiseResponse?.workflow_stage, workflowStage || 'Pending');

  const workflowIndex = useMemo(() => {
    if (!sessionId) return 0;
    if (!premiseResponse) return 1;
    if (!openingResponse) return 2;
    if (!opposingResponse) return 3;
    if (!rebuttalResponse) return 4;
    return 5;
  }, [openingResponse, opposingResponse, premiseResponse, rebuttalResponse, sessionId]);

  const judgeWorkflowStage = safeString(
    judgeEvaluation?.workflow_stage ?? rebuttalResponse?.workflow_stage ?? opposingResponse?.workflow_stage ?? openingResponse?.workflow_stage ?? premiseResponse?.workflow_stage,
    workflowSteps[Math.min(workflowIndex, workflowSteps.length - 1)]?.label ?? workflowStage,
  );

  const liveJudgeCommentary = judgeEvaluation
    ? safeString(judgeEvaluation.educational_feedback, 'Final evaluation generated.')
    : workflowIndex === 0
      ? 'Create the session to establish the courtroom context.'
      : workflowIndex === 1
        ? 'Generate the premise to lock the factual record before opening statements.'
        : workflowIndex === 2
          ? 'Draft the opening argument with a clean issue-rule-application structure.'
          : workflowIndex === 3
            ? 'The opposing counsel response is in flight. Prepare the rebuttal posture.'
            : workflowIndex === 4
              ? 'Keep the rebuttal disciplined and tied to the record.'
              : 'Review the judge evaluation and consolidate the learning points.';

  const burdenReminder = judgeEvaluation
    ? safeString(judgeEvaluation.burden_of_proof_analysis, 'Burden analysis complete.')
    : 'Keep the burden of proof explicit, and tie every assertion back to the locked facts.';

  const openingFlags = isRecord(openingResponse?.hallucination_flags)
    ? Object.entries(openingResponse.hallucination_flags).filter(([, value]) => Boolean(value)).map(([key]) => key)
    : [];
  const rebuttalFlags = isRecord(rebuttalResponse?.hallucination_flags)
    ? Object.entries(rebuttalResponse.hallucination_flags).filter(([, value]) => Boolean(value)).map(([key]) => key)
    : [];

  const openingReady = Boolean(sessionId && premiseResponse);
  const rebuttalReady = Boolean(opposingResponse);

  const handleCreateSession = async () => {
    setCreatingSession(true);
    try {
      const created = await createPracticeSession({ topic: selectedTopic, mode: selectedMode, randomize });
      setSessionId(safeString(created.session_id, ''));
      setSelectedTopic(safeString(created.topic, selectedTopic));
      setSelectedMode(safeString(created.mode, selectedMode));
      setWorkflowStage(safeString(created.workflow_stage, 'Session created'));
      setSessionStatus(normalizeStatus(created.session_status, 'active'));
      setCurrentRound(safeNumber(created.current_round, 0));
      setPremiseResponse(null);
      setOpeningArgument('');
      setOpeningResponse(null);
      setOpposingResponse(null);
      setTypedOpposing('');
      setOpposingTimestamp('');
      setRebuttalArgument('');
      setRebuttalResponse(null);
      setJudgeEvaluation(null);
      notify({ variant: 'success', title: 'Session created', message: `Session ${safeString(created.session_id, 'pending')} is ready for premise generation.` });
    } catch (error) {
      notify({ variant: 'error', title: 'Could not create session', message: getApiError(error).message });
    } finally {
      setCreatingSession(false);
    }
  };

  const handleGeneratePremise = async () => {
    if (!sessionId) {
      notify({ variant: 'info', title: 'Start a session first', message: 'Create a session before generating the premise.' });
      return;
    }
    if (!selectedTopic || !selectedMode) {
      notify({ variant: 'info', title: 'Select topic and mode', message: 'Choose both topic and mode before generating the premise.' });
      return;
    }
    setGeneratingPremise(true);
    try {
      const response = await generatePracticePremise({ sessionId, topic: selectedTopic, mode: selectedMode });
      setPremiseResponse(response);
      setWorkflowStage(safeString(response.workflow_stage, 'Premise generated'));
      setSessionStatus(normalizeStatus(response.session_status, 'awaiting-opening'));
      setCurrentRound(safeNumber(response.current_round, 0));
      notify({ variant: 'success', title: 'Premise generated', message: 'Facts are now locked and the opening editor is enabled.' });
    } catch (error) {
      notify({ variant: 'error', title: 'Could not generate premise', message: getApiError(error).message });
    } finally {
      setGeneratingPremise(false);
    }
  };

  const handleGenerateOpposing = async (source: 'auto' | 'manual' = 'auto') => {
    if (!sessionId) return;
    setGeneratingOpposing(true);
    try {
      const response = await generateOpposingCounselResponse(sessionId);
      setOpposingResponse(response);
      setOpposingTimestamp(new Date().toISOString());
      setWorkflowStage(safeString(response.workflow_stage, 'Opposing counsel response'));
      setSessionStatus(normalizeStatus(response.session_status, 'rebuttal'));
      notify({
        variant: 'success',
        title: source === 'auto' ? 'Opposing counsel response generated' : 'Opposing counsel response refreshed',
        message: 'The rebuttal editor is now available.',
      });
    } catch (error) {
      notify({ variant: 'error', title: 'Could not generate opposing response', message: getApiError(error).message });
      throw error;
    } finally {
      setGeneratingOpposing(false);
    }
  };

  const handleSubmitOpening = async () => {
    if (!sessionId) {
      notify({ variant: 'info', title: 'Create a session first', message: 'The opening argument needs an active session.' });
      return;
    }
    if (!premiseResponse) {
      notify({ variant: 'info', title: 'Generate the premise first', message: 'Lock the facts before submitting an opening argument.' });
      return;
    }
    if (!openingArgument.trim()) {
      notify({ variant: 'info', title: 'Opening argument required', message: 'Write the opening before submitting.' });
      return;
    }
    setSubmittingOpening(true);
    try {
      const response = await submitOpeningArgument({ sessionId, content: openingArgument.trim() });
      setOpeningResponse(response);
      setCurrentRound(Math.max(1, safeNumber(response.round_number ?? response.current_round, 1)));
      setWorkflowStage(safeString(response.workflow_stage, 'Opening submitted'));
      setSessionStatus(normalizeStatus(response.session_status, 'opposing-response'));
      await handleGenerateOpposing('auto');
      notify({ variant: 'success', title: 'Opening submitted', message: 'Opposing counsel has responded.' });
    } catch (error) {
      notify({ variant: 'error', title: 'Could not submit opening', message: getApiError(error).message });
    } finally {
      setSubmittingOpening(false);
    }
  };

  const handleSubmitRebuttal = async () => {
    if (!sessionId) {
      notify({ variant: 'info', title: 'Create a session first', message: 'The rebuttal needs an active session.' });
      return;
    }
    if (!opposingResponse) {
      notify({ variant: 'info', title: 'Await the opposing response', message: 'The rebuttal editor appears after opposing counsel responds.' });
      return;
    }
    if (!rebuttalArgument.trim()) {
      notify({ variant: 'info', title: 'Rebuttal required', message: 'Write the rebuttal before submitting.' });
      return;
    }
    setSubmittingRebuttal(true);
    try {
      const response = await submitRebuttalArgument({ sessionId, content: rebuttalArgument.trim() });
      setRebuttalResponse(response);
      setCurrentRound(Math.max(2, safeNumber(response.round_number ?? response.current_round, 2)));
      setWorkflowStage(safeString(response.workflow_stage, 'Rebuttal submitted'));
      setSessionStatus(normalizeStatus(response.session_status, 'judgment-complete'));
      await handleGenerateJudge('auto');
      notify({ variant: 'success', title: 'Rebuttal submitted', message: 'The judge evaluation has been generated.' });
    } catch (error) {
      notify({ variant: 'error', title: 'Could not submit rebuttal', message: getApiError(error).message });
    } finally {
      setSubmittingRebuttal(false);
    }
  };

  const handleGenerateJudge = async (source: 'auto' | 'manual' = 'manual') => {
    if (!sessionId) return;
    setGeneratingJudge(true);
    try {
      const response = await generateJudgeEvaluation(sessionId);
      setJudgeEvaluation(response);
      setWorkflowStage(safeString(response.workflow_stage, 'Judge evaluation complete'));
      setSessionStatus(normalizeStatus(response.session_status, 'judgment-complete'));
      setCurrentRound(Math.max(currentRound, safeNumber(response.current_round, currentRound)));
      notify({
        variant: 'success',
        title: source === 'auto' ? 'Judge evaluation complete' : 'Judge evaluation refreshed',
        message: `Final score ${Math.round(clamp(safeNumber(response.final_score, 0), 0, 100))}/100.`,
      });
    } catch (error) {
      notify({ variant: 'error', title: 'Could not generate judge evaluation', message: getApiError(error).message });
      throw error;
    } finally {
      setGeneratingJudge(false);
    }
  };

  const finalScore = clamp(safeNumber(judgeEvaluation?.final_score, 0), 0, 100);
  const advocacyScore = clamp(safeNumber(judgeEvaluation?.advocacy_score, 0), 0, 100);
  const proceduralDiscipline = clamp(safeNumber(judgeEvaluation?.procedural_discipline, 0), 0, 100);
  const hallucinationPenalty = clamp(safeNumber(judgeEvaluation?.hallucination_penalty, 0), 0, 100);

  const contradictionCards = judgeEvaluation?.contradictions_found ?? [];
  const learningPoints = judgeEvaluation?.learning_points ?? [];

  const premiseLoading = loadingMeta || creatingSession || generatingPremise;
  const rebuttalBusy = submittingRebuttal || generatingJudge;

  return (
    // Full-width two-panel layout — no max-width cap, gutters via px
    <div className="flex h-full min-h-screen flex-col gap-0">

      {/* ── Top header bar — full width ── */}
      <header className="border-b border-white/10 bg-[#040d19]/80 px-6 py-5 backdrop-blur-xl">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div className="space-y-1">
            <p className="section-kicker">Practice Arena</p>
            <h1 className="text-2xl font-semibold text-white lg:text-3xl">
              Courtroom workflow — session setup to judicial evaluation
            </h1>
            <p className="max-w-3xl text-sm leading-7 text-slate-400">
              Follow the staged training loop: create a session, lock the premise, draft the opening, absorb the opposing response, prepare the rebuttal, and review the final judgment.
            </p>
          </div>
          <div className="flex shrink-0 flex-wrap items-end gap-3">
            <div className="flex flex-col gap-2 rounded-3xl border border-white/10 bg-white/5 px-4 py-3">
              <p className="text-[10px] uppercase tracking-[0.28em] text-slate-500">Session setup</p>
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
                <label className="flex flex-col text-[10px] uppercase tracking-[0.28em] text-slate-500">
                  <span className="mb-1">Topic</span>
                  <select
                    value={selectedTopic}
                    onChange={(event) => setSelectedTopic(event.target.value)}
                    disabled={loadingMeta || !topics.length}
                    className="min-w-[200px] rounded-2xl border border-white/10 bg-[#06111d] px-3 py-2 text-xs text-slate-200 focus:border-electric/40 focus:outline-none disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    <option value="" disabled>
                      {loadingMeta ? 'Loading topics...' : topics.length ? 'Select topic' : 'No topics available'}
                    </option>
                    {topics.map((topic) => (
                      <option key={topic} value={topic}>
                        {topic}
                      </option>
                    ))}
                  </select>
                </label>

                <label className="flex flex-col text-[10px] uppercase tracking-[0.28em] text-slate-500">
                  <span className="mb-1">Mode</span>
                  <select
                    value={selectedMode}
                    onChange={(event) => setSelectedMode(event.target.value)}
                    disabled={loadingMeta || !modes.length}
                    className="min-w-[180px] rounded-2xl border border-white/10 bg-[#06111d] px-3 py-2 text-xs text-slate-200 focus:border-electric/40 focus:outline-none disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    <option value="" disabled>
                      {loadingMeta ? 'Loading modes...' : modes.length ? 'Select mode' : 'No modes available'}
                    </option>
                    {modes.map((mode) => (
                      <option key={mode} value={mode}>
                        {mode}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
            </div>
            <button
              type="button"
              onClick={handleCreateSession}
              disabled={creatingSession || loadingMeta}
              className="rounded-full bg-gradient-to-r from-electric to-emeraldGlow px-5 py-3 text-sm font-semibold text-white transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {creatingSession ? 'Creating Session...' : 'Create Session'}
            </button>
            <button
              type="button"
              onClick={handleGeneratePremise}
              disabled={!sessionId || premiseLoading || !selectedTopic || !selectedMode}
              className="rounded-full border border-white/15 bg-white/5 px-5 py-3 text-sm font-semibold text-white transition hover:border-electric/40 hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {generatingPremise ? 'Generating Premise...' : 'Generate Premise'}
            </button>
            <label className="flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-4 py-3 text-sm text-slate-300 cursor-pointer">
              <input type="checkbox" checked={randomize} onChange={(e) => setRandomize(e.target.checked)} className="accent-electric" />
              Randomize
            </label>
          </div>
        </div>
      </header>

      {/* ── Session metrics + stepper — full width ── */}
      <div className="border-b border-white/10 bg-[#05101a]/60 px-6 py-4 backdrop-blur-xl">
        <div className="mb-4 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
          <MetricTile label="Session ID" value={sessionId || 'Pending'} helper="Active session." />
          <MetricTile label="Topic" value={selectedTopic || 'Pending'} helper="Practice topic." />
          <MetricTile label="Mode" value={selectedMode || 'Pending'} helper="Generation mode." />
          <MetricTile label="Workflow Stage" value={workflowStage} helper="Backend workflow state." />
          <MetricTile label="Current Round" value={formatNumber(currentRound)} helper="Argument loop count." />
          <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
            <p className="text-[11px] uppercase tracking-[0.28em] text-slate-500">Session Status</p>
            <div className="mt-3">
              <StatusBadge label={sessionStatus} tone={sessionStatus} />
            </div>
          </div>
        </div>
        <StageStepper activeIndex={workflowIndex} />
      </div>

      {/* ── Main two-panel body ── */}
      <div className="flex flex-1 overflow-hidden">

        {/* LEFT PANEL — wider, scrollable, courtroom interaction */}
        <div className="flex-[1.6] overflow-y-auto border-r border-white/10 px-6 py-6">
          <div className="space-y-6">

            {/* Premise Panel */}
            <GlassCard className="min-h-[420px]" title="Premise Panel" subtitle="Generated premise, locked facts, and legal issue summary">
              <div className="space-y-4">
                <div className="grid gap-3 sm:grid-cols-2">
                  <MetricTile label="Session ID" value={premiseSessionId} />
                  <MetricTile label="Workflow Stage" value={premiseStage} />
                </div>

                <div className="rounded-3xl border border-white/10 bg-[#06111d] p-5">
                  <p className="text-xs uppercase tracking-[0.32em] text-slate-500">Premise</p>
                  <div className="mt-3 max-h-64 overflow-y-auto rounded-2xl border border-white/10 bg-[#050d18] p-4">
                    <pre className="whitespace-pre-wrap text-xs leading-6 text-slate-200">
                      {premiseText || 'Premise will appear after generation.'}
                    </pre>
                  </div>
                </div>

                <div className="space-y-3">
                  <p className="text-xs uppercase tracking-[0.32em] text-slate-500">Locked Facts</p>
                  <div className="max-h-[320px] space-y-3 overflow-y-auto pr-1">
                    {lockedFacts.length
                      ? lockedFacts.map((fact, index) => (
                        <div key={`${fact}-${index}`} className="rounded-2xl border border-amber-400/25 bg-amber-400/10 p-4 text-sm leading-7 text-amber-50 shadow-inner">
                          <p className="text-[11px] uppercase tracking-[0.28em] text-amber-200">Locked Fact {index + 1}</p>
                          <p className="mt-2 whitespace-pre-wrap">{fact}</p>
                        </div>
                      ))
                      : <EmptyPanel title="No locked facts yet" description="Generate the premise to populate the evidence record." />}
                  </div>
                </div>

                {!premiseResponse
                  ? <EmptyPanel title="Premise not generated" description="Create a session and generate the premise to unlock the opening argument stage." />
                  : null}
              </div>
            </GlassCard>

            {/* Student Advocate — Opening */}
            <GlassCard className="min-h-[420px]" title="Student Advocate" subtitle="Large legal drafting area for the opening argument">
              <div className="space-y-4">
                <div className="flex items-center gap-3 rounded-2xl border border-white/10 bg-white/5 p-4">
                  <div className="flex h-12 w-12 items-center justify-center rounded-full border border-electric/30 bg-electric/10 text-lg font-semibold text-electric">
                    A
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-white">Advocate Desk</p>
                    <p className="text-xs uppercase tracking-[0.28em] text-slate-500">Courtroom transcript style</p>
                  </div>
                </div>

                <label className="block">
                  <span className="mb-2 block text-xs uppercase tracking-[0.3em] text-slate-500">Opening Argument</span>
                  <textarea
                    value={openingArgument}
                    onChange={(e) => setOpeningArgument(e.target.value)}
                    rows={12}
                    disabled={!openingReady}
                    className="min-h-[300px] w-full rounded-3xl border border-white/10 bg-[#06111d] px-4 py-4 text-sm leading-7 text-white placeholder:text-slate-500 focus:border-electric/40 focus:outline-none disabled:cursor-not-allowed disabled:opacity-60"
                    placeholder={openingReady ? 'Frame the issue, state the rule, and anchor your facts.' : 'Generate the premise to unlock the opening editor.'}
                  />
                </label>

                <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
                  <p className="text-sm text-slate-400">
                    Legal writing helper placeholder: open with the issue, keep the rule tight, and connect every paragraph to the locked facts.
                  </p>
                  <p className="text-xs uppercase tracking-[0.28em] text-slate-500">{formatNumber(openingArgument.length)} characters</p>
                </div>

                <div className="flex flex-wrap items-center gap-3">
                  <button
                    type="button"
                    onClick={handleSubmitOpening}
                    disabled={!openingReady || submittingOpening || generatingOpposing}
                    className="rounded-full bg-gradient-to-r from-electric to-emeraldGlow px-5 py-3 text-sm font-semibold text-white transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {submittingOpening ? 'Submitting Opening...' : generatingOpposing ? 'Generating Opposing Response...' : 'Submit Opening Argument'}
                  </button>
                  <StatusBadge label={openingReady ? 'Ready for opening' : 'Awaiting premise'} tone={openingReady ? 'awaiting-opening' : 'active'} />
                </div>

                {openingResponse ? (
                  <div className="rounded-3xl border border-electric/30 bg-electric/10 p-5">
                    <p className="text-xs uppercase tracking-[0.28em] text-electric">Opening Record</p>
                    <p className="mt-3 whitespace-pre-wrap text-sm leading-7 text-white">{safeString(openingResponse.content, openingArgument)}</p>
                    <div className="mt-4 flex flex-wrap items-center gap-2 text-xs text-slate-400">
                      <span>Round {Math.max(1, safeNumber(openingResponse.round_number ?? openingResponse.current_round, 1))}</span>
                      <span>•</span>
                      <span>{safeString(openingResponse.argument_type, 'opening')}</span>
                      {openingFlags.length ? (
                        <>
                          <span>•</span>
                          <span className="text-amber-300">Hallucination flags: {openingFlags.join(', ')}</span>
                        </>
                      ) : null}
                    </div>
                  </div>
                ) : null}
              </div>
            </GlassCard>

            {/* Opposing Counsel Response */}
            <GlassCard className="min-h-[360px]" title="Opposing Counsel Response" subtitle="Auto-generated challenge after the opening argument is submitted">
              {opposingResponse ? (
                <div className="space-y-4 rounded-3xl border border-rose-400/25 bg-rose-500/10 p-5">
                  <div className="flex items-center justify-between gap-4">
                    <div className="flex items-center gap-3">
                      <div className="flex h-11 w-11 items-center justify-center rounded-full border border-rose-200/30 bg-rose-200/10 text-sm font-semibold text-rose-100">
                        AI
                      </div>
                      <div>
                        <p className="text-sm font-semibold text-white">AI Opposing Counsel</p>
                        <p className="text-xs uppercase tracking-[0.28em] text-rose-200">Legal challenge transcript</p>
                      </div>
                    </div>
                    <div className="text-right text-xs uppercase tracking-[0.22em] text-rose-200">
                      <p>{opposingTimestamp ? formatDateTime(opposingTimestamp) : 'Pending'}</p>
                      <p className="mt-1 text-[10px] tracking-[0.28em] text-rose-300/80">Typing animation enabled</p>
                    </div>
                  </div>

                  <div className="rounded-2xl border border-white/10 bg-[#06111d] p-4">
                    <p className="mb-3 text-xs uppercase tracking-[0.28em] text-slate-500">Courtroom Dialogue</p>
                    <p className="whitespace-pre-wrap text-sm leading-8 text-slate-100">
                      {typedOpposing || safeString(opposingResponse.content, 'The opposing counsel response will appear here.')}
                    </p>
                  </div>

                  <div className="flex flex-wrap items-center gap-2 text-xs text-slate-300">
                    <StatusBadge label={sessionStatus} tone={sessionStatus} />
                    <span>{safeString(opposingResponse.workflow_stage, workflowStage)}</span>
                  </div>

                  <button
                    type="button"
                    onClick={() => void handleGenerateOpposing('manual').catch(() => undefined)}
                    disabled={generatingOpposing}
                    className="rounded-full border border-rose-200/30 bg-rose-200/10 px-4 py-2 text-sm font-semibold text-rose-50 transition hover:bg-rose-200/15 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {generatingOpposing ? 'Refreshing...' : 'Regenerate Opposing Response'}
                  </button>
                </div>
              ) : openingResponse ? (
                <div className="space-y-3 rounded-3xl border border-white/10 bg-white/5 p-5">
                  <LoadingSpinner label="Generating opposing counsel response" />
                  <p className="text-sm leading-7 text-slate-400">The next courtroom stage is generating now. The rebuttal editor will unlock after the response is returned.</p>
                </div>
              ) : (
                <EmptyPanel title="Opposing response pending" description="Submit the opening argument to trigger the AI opposing counsel challenge." />
              )}
            </GlassCard>

            {/* Rebuttal */}
            <GlassCard className="min-h-[360px]" title="Rebuttal" subtitle="Respond after the opposing counsel challenge appears">
              <div className="space-y-4">
                <div className="flex items-center gap-3 rounded-2xl border border-white/10 bg-white/5 p-4">
                  <div className="flex h-12 w-12 items-center justify-center rounded-full border border-emeraldGlow/30 bg-emeraldGlow/10 text-lg font-semibold text-emeraldGlow">
                    R
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-white">Rebuttal Desk</p>
                    <p className="text-xs uppercase tracking-[0.28em] text-slate-500">Procedural note: answer only the points raised by opposing counsel.</p>
                  </div>
                </div>

                <label className="block">
                  <span className="mb-2 block text-xs uppercase tracking-[0.3em] text-slate-500">Rebuttal Argument</span>
                  <textarea
                    value={rebuttalArgument}
                    onChange={(e) => setRebuttalArgument(e.target.value)}
                    rows={10}
                    disabled={!rebuttalReady}
                    className="min-h-[250px] w-full rounded-3xl border border-white/10 bg-[#06111d] px-4 py-4 text-sm leading-7 text-white placeholder:text-slate-500 focus:border-electric/40 focus:outline-none disabled:cursor-not-allowed disabled:opacity-60"
                    placeholder={rebuttalReady ? 'Target the objection, preserve the record, and respond with discipline.' : 'Wait for the opposing response to unlock rebuttal drafting.'}
                  />
                </label>

                <div className="flex items-center justify-between gap-4 text-sm text-slate-400">
                  <p>Legal drafting style: concise, procedural, and grounded in the record.</p>
                  <p className="text-xs uppercase tracking-[0.28em] text-slate-500">{formatNumber(rebuttalArgument.length)} characters</p>
                </div>

                <div className="flex flex-wrap items-center gap-3">
                  <button
                    type="button"
                    onClick={handleSubmitRebuttal}
                    disabled={!rebuttalReady || submittingRebuttal || generatingJudge}
                    className="rounded-full border border-white/15 bg-white/5 px-5 py-3 text-sm font-semibold text-white transition hover:border-electric/40 hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {submittingRebuttal ? 'Submitting Rebuttal...' : generatingJudge ? 'Generating Judge Evaluation...' : 'Submit Rebuttal'}
                  </button>
                  <StatusBadge label={rebuttalReady ? 'Ready for rebuttal' : 'Awaiting opposing counsel'} tone={rebuttalReady ? 'rebuttal' : 'active'} />
                </div>

                {rebuttalResponse ? (
                  <div className="rounded-3xl border border-emeraldGlow/30 bg-emeraldGlow/10 p-5">
                    <p className="text-xs uppercase tracking-[0.28em] text-emeraldGlow">Rebuttal Record</p>
                    <p className="mt-3 whitespace-pre-wrap text-sm leading-7 text-white">{safeString(rebuttalResponse.content, rebuttalArgument)}</p>
                    <div className="mt-4 flex flex-wrap items-center gap-2 text-xs text-slate-400">
                      <span>Round {Math.max(2, safeNumber(rebuttalResponse.round_number ?? rebuttalResponse.current_round, 2))}</span>
                      <span>•</span>
                      <span>{safeString(rebuttalResponse.argument_type, 'rebuttal')}</span>
                      {rebuttalFlags.length ? (
                        <>
                          <span>•</span>
                          <span className="text-rose-200">Hallucination flags: {rebuttalFlags.join(', ')}</span>
                        </>
                      ) : null}
                    </div>
                  </div>
                ) : null}
              </div>
            </GlassCard>

          </div>
        </div>

        {/* RIGHT PANEL — narrower, sticky scrollable, judge analysis */}
        <div className="flex-1 overflow-y-auto px-6 py-6">
          <div className="space-y-4">

            {/* Judge Analysis — live */}
            <GlassCard className="min-h-[280px]" title="Judge Analysis" subtitle="Live remarks that update as the session progresses">
              <div className="space-y-4">
                <div className="flex items-center gap-3 rounded-2xl border border-mutedGold/25 bg-mutedGold/10 p-4">
                  <div className="flex h-12 w-12 items-center justify-center rounded-full border border-mutedGold/35 bg-mutedGold/15 text-lg font-semibold text-mutedGold">
                    J
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-white">Judge Panel</p>
                    <p className="text-xs uppercase tracking-[0.28em] text-mutedGold">Workflow stage: {judgeWorkflowStage}</p>
                  </div>
                </div>

                <div className="space-y-3">
                  <MetricTile label="Procedural Notes" value={workflowStage} helper="The backend workflow stage rendered in the judge panel." />
                  <MetricTile label="Judge Commentary" value={liveJudgeCommentary} helper="Live remarks update after each stage." />
                  <MetricTile label="Burden Reminder" value={burdenReminder} helper="Keep the burden of proof and record discipline explicit." />
                </div>
              </div>
            </GlassCard>

            {/* Final Judge Evaluation */}
            <GlassCard className="min-h-[520px]" title="Final Judge Evaluation" subtitle="Each field is displayed separately once the judge endpoint responds">
              <div className="space-y-4">
                {judgeEvaluation ? (
                  <>
                    <JudgeCard title="Burden of Proof Analysis">
                      <p className="whitespace-pre-wrap text-sm leading-7 text-slate-200">{safeString(judgeEvaluation.burden_of_proof_analysis, 'No burden analysis returned.')}</p>
                    </JudgeCard>

                    <JudgeCard title="Contradictions Found">
                      {contradictionCards.length ? (
                        <div className="space-y-2">
                          {contradictionCards.map((item, index) => (
                            <div key={`${item}-${index}`} className="rounded-2xl border border-rose-400/25 bg-rose-500/10 p-4 text-sm leading-7 text-rose-50">
                              {item}
                            </div>
                          ))}
                        </div>
                      ) : (
                        <p className="text-sm leading-7 text-slate-400">No contradictions were reported.</p>
                      )}
                    </JudgeCard>

                    <JudgeCard title="Evidentiary Sufficiency">
                      <p className="whitespace-pre-wrap text-sm leading-7 text-slate-200">{safeString(judgeEvaluation.evidentiary_sufficiency, 'No evidentiary sufficiency analysis returned.')}</p>
                    </JudgeCard>

                    <CircularScoreMeter score={advocacyScore} label="Advocacy Score" />

                    <JudgeCard title="Procedural Discipline">
                      <ScoreMeter score={proceduralDiscipline} label="Courtroom discipline score" />
                    </JudgeCard>

                    <JudgeCard title="Hallucination Penalty">
                      <div className="rounded-2xl border border-rose-400/25 bg-rose-500/10 p-4">
                        <p className="text-3xl font-semibold text-rose-100">{Math.round(hallucinationPenalty)}</p>
                        <p className="mt-2 text-sm text-rose-100/80">Red warning indicator for unsupported or speculative content.</p>
                      </div>
                    </JudgeCard>

                    <JudgeCard title="Educational Feedback">
                      <p className="whitespace-pre-wrap text-sm leading-7 text-slate-200">{safeString(judgeEvaluation.educational_feedback, 'No educational feedback returned.')}</p>
                    </JudgeCard>

                    <div className="rounded-3xl border border-mutedGold/30 bg-gradient-to-r from-mutedGold/20 via-mutedGold/10 to-transparent p-5">
                      <p className="text-xs uppercase tracking-[0.28em] text-mutedGold">Termination Recommendation</p>
                      <p className="mt-3 whitespace-pre-wrap text-sm leading-7 text-white">
                        {safeString(judgeEvaluation.termination_recommendation, 'No termination recommendation returned.')}
                      </p>
                    </div>

                    <JudgeCard title="Learning Points">
                      {learningPoints.length ? (
                        <div className="grid gap-3 sm:grid-cols-2">
                          {learningPoints.map((point, index) => (
                            <div key={`${point}-${index}`} className="rounded-2xl border border-white/10 bg-white/5 p-4 text-sm leading-7 text-slate-200">
                              {point}
                            </div>
                          ))}
                        </div>
                      ) : (
                        <p className="text-sm leading-7 text-slate-400">No learning points returned.</p>
                      )}
                    </JudgeCard>

                    <ScoreRibbon score={finalScore} />

                    <button
                      type="button"
                      onClick={() => void handleGenerateJudge('manual').catch(() => undefined)}
                      disabled={generatingJudge}
                      className="rounded-full border border-mutedGold/30 bg-mutedGold/10 px-4 py-2 text-sm font-semibold text-mutedGold transition hover:bg-mutedGold/15 disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      {generatingJudge ? 'Refreshing Judge Evaluation...' : 'Regenerate Judge Evaluation'}
                    </button>
                  </>
                ) : (
                  <div className="space-y-4">
                    <EmptyPanel title="Judge evaluation pending" description="Submit the rebuttal to unlock the final judge analysis and score cards." />
                    <LoadingSpinner label={rebuttalBusy ? 'Generating judge evaluation' : 'Waiting for session workflow'} />
                  </div>
                )}
              </div>
            </GlassCard>

          </div>
        </div>

      </div>
    </div>
  );
}