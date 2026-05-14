import { useEffect, useMemo, useState, type ReactNode } from 'react';
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

// ─── Types ────────────────────────────────────────────────────────────────────

type SessionStatus = 'active' | 'awaiting-opening' | 'opposing-response' | 'rebuttal' | 'judgment-complete';

type WorkflowStep = { label: string; description: string };

const workflowSteps: WorkflowStep[] = [
  { label: 'Create Session',   description: 'Open a new practice arena session.' },
  { label: 'Generate Premise', description: 'Lock the facts and legal issue.' },
  { label: 'Opening Argument', description: 'Submit the student advocate draft.' },
  { label: 'Opposing Counsel', description: 'Render the AI challenge response.' },
  { label: 'Rebuttal',         description: 'Draft the follow-up response.' },
  { label: 'Judge Evaluation', description: 'Review the final assessment.' },
];

const statusTone: Record<SessionStatus, string> = {
  'active':            'border-blue-200    bg-blue-50    text-blue-700',
  'awaiting-opening':  'border-amber-300   bg-amber-50   text-amber-700',
  'opposing-response': 'border-orange-300  bg-orange-50  text-orange-700',
  'rebuttal':          'border-emerald-300 bg-emerald-50 text-emerald-700',
  'judgment-complete': 'border-amber-400   bg-amber-100  text-amber-800',
};

// ─── Helpers ──────────────────────────────────────────────────────────────────

function isRecord(v: unknown): v is Record<string, unknown> {
  return Boolean(v) && typeof v === 'object' && !Array.isArray(v);
}

function normalizeStatus(raw: unknown, fallback: SessionStatus): SessionStatus {
  const v = safeString(raw, fallback).toLowerCase();
  if (v.includes('awaiting-opening'))              return 'awaiting-opening';
  if (v.includes('opposing'))                      return 'opposing-response';
  if (v.includes('rebuttal'))                      return 'rebuttal';
  if (v.includes('judge') || v.includes('complete')) return 'judgment-complete';
  if (v.includes('active') || v.includes('session-created')) return 'active';
  return fallback;
}

// ─── Shared atoms ─────────────────────────────────────────────────────────────

function Badge({ label, tone }: { label: string; tone: SessionStatus | 'neutral' }) {
  return (
    <span className={classNames(
      'inline-flex items-center rounded-full border px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-widest',
      tone === 'neutral' ? 'border-slate-200 bg-white text-slate-500' : statusTone[tone],
    )}>
      {label}
    </span>
  );
}

function SectionLabel({ children }: { children: ReactNode }) {
  return <p className="text-[10px] font-bold uppercase tracking-[0.3em] text-slate-800">{children}</p>;
}

function Divider() {
  return <hr className="border-slate-100" />;
}

function Empty({ text }: { text: string }) {
  return <p className="text-sm italic text-slate-800">{text}</p>;
}

function JSection({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="space-y-2">
      <SectionLabel>{title}</SectionLabel>
      {children}
    </div>
  );
}

// ─── Step progress bar ────────────────────────────────────────────────────────

function StepBar({ activeIndex }: { activeIndex: number }) {
  return (
    <div className="flex items-center">
      {workflowSteps.map((step, i) => {
        const done    = i < activeIndex;
        const current = i === activeIndex;
        return (
          <div key={step.label} className="flex flex-1 items-center">
            <div className="flex flex-col items-center gap-1">
              <div className={classNames(
                'flex h-7 w-7 items-center justify-center rounded-full border-2 text-xs font-bold transition-all',
                done    ? 'border-emerald-400 bg-emerald-400 text-white'
                : current ? 'border-orange-500 bg-orange-500 text-white'
                :           'border-slate-200  bg-white       text-slate-800',
              )}>
                {done ? '✓' : i + 1}
              </div>
              <span className={classNames(
                'hidden text-[9px] font-semibold uppercase tracking-wider xl:block',
                done ? 'text-emerald-500' : current ? 'text-orange-500' : 'text-slate-800',
              )}>
                {step.label}
              </span>
            </div>
            {i < workflowSteps.length - 1 && (
              <div className={classNames('h-0.5 flex-1 transition-all', done ? 'bg-emerald-300' : 'bg-slate-200')} />
            )}
          </div>
        );
      })}
    </div>
  );
}

// ─── Score ring ───────────────────────────────────────────────────────────────

function ScoreRing({ score, label }: { score: number; label: string }) {
  const v   = clamp(score, 0, 100);
  const deg = v * 3.6;
  return (
    <div className="flex items-center gap-4">
      <div
        className="relative flex h-16 w-16 shrink-0 items-center justify-center rounded-full"
        style={{ background: `conic-gradient(#f59e0b 0deg ${deg}deg, #f3f4f6 ${deg}deg 360deg)` }}
      >
        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-white">
          <span className="text-sm font-bold text-slate-900">{Math.round(v)}</span>
        </div>
      </div>
      <div>
        <p className="text-xs uppercase tracking-wider text-slate-800">{label}</p>
        <p className="text-lg font-bold text-slate-900">{formatPercent(v)}</p>
      </div>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export function PracticeArenaPage() {
  const { notify } = useToast();

  const [topics, setTopics]               = useState<string[]>([]);
  const [modes, setModes]                 = useState<string[]>([]);
  const [loadingMeta, setLoadingMeta]     = useState(true);
  const [selectedTopic, setSelectedTopic] = useState('');
  const [selectedMode, setSelectedMode]   = useState('');
  const [randomize, setRandomize]         = useState(true);

  const [sessionId, setSessionId]           = useState('');
  const [workflowStage, setWorkflowStage]   = useState('Create Session');
  const [sessionStatus, setSessionStatus]   = useState<SessionStatus>('active');
  const [currentRound, setCurrentRound]     = useState(0);

  const [premiseResponse, setPremiseResponse]     = useState<PracticePremiseResponse | null>(null);
  const [openingArgument, setOpeningArgument]     = useState('');
  const [openingResponse, setOpeningResponse]     = useState<PracticeWorkflowArgumentResponse | null>(null);
  const [opposingResponse, setOpposingResponse]   = useState<PracticeOpposingResponse | null>(null);
  const [typedOpposing, setTypedOpposing]         = useState('');
  const [opposingTimestamp, setOpposingTimestamp] = useState('');
  const [rebuttalArgument, setRebuttalArgument]   = useState('');
  const [rebuttalResponse, setRebuttalResponse]   = useState<PracticeWorkflowArgumentResponse | null>(null);
  const [judgeEvaluation, setJudgeEvaluation]     = useState<PracticeJudgeEvaluationResponse | null>(null);

  const [creatingSession, setCreatingSession]       = useState(false);
  const [generatingPremise, setGeneratingPremise]   = useState(false);
  const [submittingOpening, setSubmittingOpening]   = useState(false);
  const [generatingOpposing, setGeneratingOpposing] = useState(false);
  const [submittingRebuttal, setSubmittingRebuttal] = useState(false);
  const [generatingJudge, setGeneratingJudge]       = useState(false);

  useEffect(() => {
    Promise.all([getPremiseTopics(), getPremiseModes()])
      .then(([t, m]) => {
        setTopics(t); setModes(m);
        setSelectedTopic(t[0] ?? ''); setSelectedMode(m[0] ?? '');
      })
      .catch(err => notify({ variant: 'error', title: 'Could not load options', message: getApiError(err).message }))
      .finally(() => setLoadingMeta(false));
  }, [notify]);

  useEffect(() => {
    const content = safeString(opposingResponse?.content, '');
    if (!content) { setTypedOpposing(''); setOpposingTimestamp(''); return; }
    let i = 0; setTypedOpposing('');
    const step = Math.max(1, Math.ceil(content.length / 120));
    const t = window.setInterval(() => {
      i += step; setTypedOpposing(content.slice(0, i));
      if (i >= content.length) window.clearInterval(t);
    }, 16);
    return () => window.clearInterval(t);
  }, [opposingResponse]);

  const premiseText = useMemo(() => {
    const p = premiseResponse?.premise;
    return isRecord(p) ? safeString(p.scenario_text, '') : safeString(p, '');
  }, [premiseResponse]);
  const lockedFacts = premiseResponse?.locked_facts ?? [];

  const workflowIndex = useMemo(() => {
    if (!sessionId)      return 0;
    if (!premiseResponse)  return 1;
    if (!openingResponse)  return 2;
    if (!opposingResponse) return 3;
    if (!rebuttalResponse) return 4;
    return 5;
  }, [sessionId, premiseResponse, openingResponse, opposingResponse, rebuttalResponse]);

  const judgeSpeech = useMemo(() => {
    if (!judgeEvaluation) return '';
    return [
      judgeEvaluation.burden_of_proof_analysis,
      judgeEvaluation.evidentiary_sufficiency,
      judgeEvaluation.educational_feedback,
      judgeEvaluation.termination_recommendation,
    ].filter(Boolean).map(s => safeString(s, '')).join('\n\n');
  }, [judgeEvaluation]);

  const opposingSpeech = safeString(opposingResponse?.content, '').trim();

  const pickVoice = (voices: SpeechSynthesisVoice[], role: 'judge' | 'opposing') => {
    const keys = role === 'judge'
      ? ['male','man','deep','bass','david','mark','george','james','daniel','brian','steve']
      : ['deep','bass','male','man','david','mark','george','james'];
    const items = voices.map(v => ({ v, n: `${v.name} ${v.voiceURI}`.toLowerCase() }));
    return items.find(({ n }) => keys.some(k => n.includes(k)))?.v
      ?? voices.find(v => v.lang.startsWith('en'))
      ?? voices[0];
  };
  const speak = (text: string, role: 'judge' | 'opposing') => {
    if (!('speechSynthesis' in window) || !text.trim()) return;
    const u = new SpeechSynthesisUtterance(text.trim());
    const voice = pickVoice(window.speechSynthesis.getVoices(), role);
    if (voice) u.voice = voice;
    u.pitch = role === 'judge' ? 0.6 : 0.7;
    u.rate  = role === 'judge' ? 0.9 : 0.95;
    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(u);
  };
  const stopSpeech = () => { if ('speechSynthesis' in window) window.speechSynthesis.cancel(); };

  // ── Handlers ──────────────────────────────────────────────────────────────

  const handleCreateSession = async () => {
    setCreatingSession(true);
    try {
      const c = await createPracticeSession({ topic: selectedTopic, mode: selectedMode, randomize });
      setSessionId(safeString(c.session_id, ''));
      setSelectedTopic(safeString(c.topic, selectedTopic));
      setSelectedMode(safeString(c.mode, selectedMode));
      setWorkflowStage(safeString(c.workflow_stage, 'Session created'));
      setSessionStatus(normalizeStatus(c.session_status, 'active'));
      setCurrentRound(safeNumber(c.current_round, 0));
      setPremiseResponse(null); setOpeningArgument(''); setOpeningResponse(null);
      setOpposingResponse(null); setTypedOpposing(''); setOpposingTimestamp('');
      setRebuttalArgument(''); setRebuttalResponse(null); setJudgeEvaluation(null);
      notify({ variant: 'success', title: 'Session created', message: `${safeString(c.session_id, 'pending')} ready.` });
    } catch (e) {
      notify({ variant: 'error', title: 'Could not create session', message: getApiError(e).message });
    } finally { setCreatingSession(false); }
  };

  const handleGeneratePremise = async () => {
    if (!sessionId) { notify({ variant: 'info', title: 'Start a session first' }); return; }
    setGeneratingPremise(true);
    try {
      const r = await generatePracticePremise({ sessionId, topic: selectedTopic, mode: selectedMode });
      setPremiseResponse(r);
      setWorkflowStage(safeString(r.workflow_stage, 'Premise generated'));
      setSessionStatus(normalizeStatus(r.session_status, 'awaiting-opening'));
      setCurrentRound(safeNumber(r.current_round, 0));
      notify({ variant: 'success', title: 'Premise generated' });
    } catch (e) {
      notify({ variant: 'error', title: 'Could not generate premise', message: getApiError(e).message });
    } finally { setGeneratingPremise(false); }
  };

  const handleGenerateOpposing = async (source: 'auto' | 'manual' = 'auto') => {
    if (!sessionId) return;
    setGeneratingOpposing(true);
    try {
      const r = await generateOpposingCounselResponse(sessionId);
      setOpposingResponse(r); setOpposingTimestamp(new Date().toISOString());
      setWorkflowStage(safeString(r.workflow_stage, 'Opposing counsel response'));
      setSessionStatus(normalizeStatus(r.session_status, 'rebuttal'));
      notify({ variant: 'success', title: source === 'auto' ? 'Opposing response generated' : 'Opposing response refreshed' });
    } catch (e) {
      notify({ variant: 'error', title: 'Could not generate opposing response', message: getApiError(e).message });
      throw e;
    } finally { setGeneratingOpposing(false); }
  };

  const handleSubmitOpening = async () => {
    if (!sessionId || !premiseResponse || !openingArgument.trim()) {
      notify({ variant: 'info', title: 'Opening argument required' }); return;
    }
    setSubmittingOpening(true);
    try {
      const r = await submitOpeningArgument({ sessionId, content: openingArgument.trim() });
      setOpeningResponse(r);
      setCurrentRound(Math.max(1, safeNumber(r.round_number ?? r.current_round, 1)));
      setWorkflowStage(safeString(r.workflow_stage, 'Opening submitted'));
      setSessionStatus(normalizeStatus(r.session_status, 'opposing-response'));
      await handleGenerateOpposing('auto');
    } catch (e) {
      notify({ variant: 'error', title: 'Could not submit opening', message: getApiError(e).message });
    } finally { setSubmittingOpening(false); }
  };

  const handleSubmitRebuttal = async () => {
    if (!sessionId || !opposingResponse || !rebuttalArgument.trim()) {
      notify({ variant: 'info', title: 'Rebuttal required' }); return;
    }
    setSubmittingRebuttal(true);
    try {
      const r = await submitRebuttalArgument({ sessionId, content: rebuttalArgument.trim() });
      setRebuttalResponse(r);
      setCurrentRound(Math.max(2, safeNumber(r.round_number ?? r.current_round, 2)));
      setWorkflowStage(safeString(r.workflow_stage, 'Rebuttal submitted'));
      setSessionStatus(normalizeStatus(r.session_status, 'judgment-complete'));
      await handleGenerateJudge('auto');
    } catch (e) {
      notify({ variant: 'error', title: 'Could not submit rebuttal', message: getApiError(e).message });
    } finally { setSubmittingRebuttal(false); }
  };

  const handleGenerateJudge = async (source: 'auto' | 'manual' = 'manual') => {
    if (!sessionId) return;
    setGeneratingJudge(true);
    try {
      const r = await generateJudgeEvaluation(sessionId);
      setJudgeEvaluation(r);
      setWorkflowStage(safeString(r.workflow_stage, 'Judge evaluation complete'));
      setSessionStatus(normalizeStatus(r.session_status, 'judgment-complete'));
      setCurrentRound(Math.max(currentRound, safeNumber(r.current_round, currentRound)));
      notify({
        variant: 'success',
        title: source === 'auto' ? 'Judge evaluation complete' : 'Evaluation refreshed',
        message: `Score: ${Math.round(clamp(safeNumber(r.final_score, 0), 0, 100))}/100`,
      });
    } catch (e) {
      notify({ variant: 'error', title: 'Could not generate evaluation', message: getApiError(e).message });
      throw e;
    } finally { setGeneratingJudge(false); }
  };

  const finalScore       = clamp(safeNumber(judgeEvaluation?.final_score,          0), 0, 100);
  const advocacyScore    = clamp(safeNumber(judgeEvaluation?.advocacy_score,        0), 0, 100);
  const proceduralDisc   = clamp(safeNumber(judgeEvaluation?.procedural_discipline, 0), 0, 100);
  const hallucinationPen = clamp(safeNumber(judgeEvaluation?.hallucination_penalty, 0), 0, 100);
  const contradictions   = judgeEvaluation?.contradictions_found ?? [];
  const learningPoints   = judgeEvaluation?.learning_points       ?? [];

  const openingReady   = Boolean(sessionId && premiseResponse);
  const rebuttalReady  = Boolean(opposingResponse);
  const premiseLoading = loadingMeta || creatingSession || generatingPremise;
  const rebuttalBusy   = submittingRebuttal || generatingJudge;

  const openingFlags  = isRecord(openingResponse?.hallucination_flags)
    ? Object.entries(openingResponse.hallucination_flags).filter(([, v]) => Boolean(v)).map(([k]) => k) : [];
  const rebuttalFlags = isRecord(rebuttalResponse?.hallucination_flags)
    ? Object.entries(rebuttalResponse.hallucination_flags).filter(([, v]) => Boolean(v)).map(([k]) => k) : [];

  // ── Render ─────────────────────────────────────────────────────────────────

  return (
    <div className="flex h-[calc(100vh-64px)] min-h-0 flex-col bg-slate-50 p-3">

      {/* ── Top bar ───────────────────────────────────────────────────────── */}
      <div className="shrink-0 border-b border-slate-200 bg-white px-6 py-3">
        <div className="flex flex-wrap items-center justify-between gap-3">

          {/* Step progress */}
          <div className="min-w-0 flex-1">
            <StepBar activeIndex={workflowIndex} />
          </div>

          {/* Controls */}
          <div className="flex shrink-0 flex-wrap items-center gap-2">
            {!sessionId && (
              <>
                <select value={selectedTopic} onChange={e => setSelectedTopic(e.target.value)}
                  disabled={loadingMeta || !topics.length}
                  className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-700 focus:outline-none disabled:opacity-50">
                  <option value="" disabled>{loadingMeta ? 'Loading…' : 'Select topic'}</option>
                  {topics.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
                <select value={selectedMode} onChange={e => setSelectedMode(e.target.value)}
                  disabled={loadingMeta || !modes.length}
                  className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-700 focus:outline-none disabled:opacity-50">
                  <option value="" disabled>{loadingMeta ? 'Loading…' : 'Select mode'}</option>
                  {modes.map(m => <option key={m} value={m}>{m}</option>)}
                </select>
                <label className="flex cursor-pointer items-center gap-1.5 text-xs text-slate-600">
                  <input type="checkbox" checked={randomize} onChange={e => setRandomize(e.target.checked)} className="accent-orange-500" />
                  Randomize
                </label>
              </>
            )}

            {sessionId && (
              <span className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs text-slate-500">
                <span className="font-semibold text-slate-700">{sessionId}</span>
                {' · '}Round {currentRound}{' · '}{selectedTopic}
              </span>
            )}

            <Badge label={sessionStatus} tone={sessionStatus} />

            <button onClick={handleCreateSession} disabled={creatingSession || loadingMeta}
              className="rounded-full bg-orange-500 px-4 py-1.5 text-xs font-semibold text-white hover:bg-orange-600 disabled:opacity-50">
              {creatingSession ? 'Creating…' : sessionId ? 'New Session' : 'Create Session'}
            </button>
            <button onClick={handleGeneratePremise} disabled={!sessionId || premiseLoading}
              className="rounded-full border border-slate-200 bg-white px-4 py-1.5 text-xs font-semibold text-slate-700 hover:border-orange-300 hover:bg-orange-50 disabled:opacity-50">
              {generatingPremise ? 'Generating…' : 'Generate Premise'}
            </button>
          </div>

        </div>
      </div>

      {/* ── Two-panel body ────────────────────────────────────────────────── */}
      <div className="flex min-h-0 flex-1 overflow-hidden">

        {/* ══ LEFT PANEL — courtroom interaction ══════════════════════════ */}
        <div className="flex flex-[1.55] flex-col overflow-y-auto border-r border-slate-200 bg-white">
          <div className="divide-y divide-slate-100">

            {/* Premise */}
            <section className="space-y-4 px-7 py-6">
              <SectionLabel>Premise</SectionLabel>
              {premiseResponse ? (
                <div className="grid gap-5 lg:grid-cols-[1.35fr_0.65fr]">
                  <p className="text-sm leading-7 text-slate-700 whitespace-pre-wrap">
                    {premiseText || 'Premise narrative will appear here.'}
                  </p>
                  {/* Locked facts — the ONE intentional inner scroll since lists can be long */}
                  <div className="space-y-2">
                    <p className="text-[10px] font-semibold uppercase tracking-widest text-slate-800">Locked Facts</p>
                    <div className="max-h-52 space-y-1.5 overflow-y-auto pr-1">
                      {lockedFacts.length
                        ? lockedFacts.map((f, i) => (
                          <div key={i} className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs leading-6 text-amber-800">
                            <span className="mr-2 font-bold text-amber-400">#{i + 1}</span>{f}
                          </div>
                        ))
                        : <p className="text-xs text-slate-800">No locked facts yet.</p>}
                    </div>
                  </div>
                </div>
              ) : (
                <Empty text={sessionId ? 'Click "Generate Premise" to lock the factual record.' : 'Create a session to get started.'} />
              )}
            </section>

            {/* Opening argument */}
            <section className="space-y-4 px-7 py-6">
              <div className="flex items-center justify-between">
                <SectionLabel>Opening Argument — Student Advocate</SectionLabel>
                {openingResponse && (
                  <span className="text-[10px] text-slate-800">
                    Round {Math.max(1, safeNumber(openingResponse.round_number ?? openingResponse.current_round, 1))}
                    {openingFlags.length ? ` · ⚠ ${openingFlags.join(', ')}` : ''}
                  </span>
                )}
              </div>

              <textarea
                value={openingArgument}
                onChange={e => setOpeningArgument(e.target.value)}
                rows={8}
                disabled={!openingReady}
                className="w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm leading-7 text-slate-900 placeholder:text-slate-800 focus:border-orange-300 focus:bg-white focus:outline-none disabled:cursor-not-allowed disabled:opacity-50"
                placeholder={openingReady
                  ? 'Frame the issue, state the rule, anchor every point to the locked facts.'
                  : 'Generate the premise first.'}
              />

              <div className="flex items-center justify-between">
                <button onClick={handleSubmitOpening}
                  disabled={!openingReady || submittingOpening || generatingOpposing}
                  className="rounded-full bg-orange-500 px-5 py-2 text-sm font-semibold text-white hover:bg-orange-600 disabled:opacity-50">
                  {submittingOpening ? 'Submitting…' : generatingOpposing ? 'Generating opposing response…' : 'Submit Opening'}
                </button>
                <span className="text-xs text-slate-800">{formatNumber(openingArgument.length)} chars</span>
              </div>
            </section>

            {/* Opposing counsel */}
            <section className="space-y-4 px-7 py-6">
              <div className="flex items-center justify-between">
                <SectionLabel>Opposing Counsel Response</SectionLabel>
                {opposingResponse && (
                  <div className="flex items-center gap-2">
                    <button onClick={() => speak(opposingSpeech, 'opposing')} disabled={!opposingSpeech}
                      className="rounded-full border border-slate-200 px-3 py-1 text-[10px] font-semibold text-slate-600 hover:border-orange-300 hover:text-orange-600 disabled:opacity-40">
                      ▶ Listen
                    </button>
                    <button onClick={stopSpeech}
                      className="rounded-full border border-slate-200 px-3 py-1 text-[10px] font-semibold text-slate-500 hover:border-slate-300">
                      ■ Stop
                    </button>
                  </div>
                )}
              </div>

              {opposingResponse ? (
                <div className="space-y-3">
                  <div className="rounded-xl border border-orange-100 bg-orange-50 px-4 py-3">
                    <p className="whitespace-pre-wrap text-sm leading-7 text-orange-900">
                      {typedOpposing || safeString(opposingResponse.content, '')}
                    </p>
                  </div>
                  <div className="flex items-center justify-between text-xs text-slate-800">
                    <span>{opposingTimestamp ? `Generated ${formatDateTime(opposingTimestamp)}` : ''}</span>
                    <button onClick={() => void handleGenerateOpposing('manual').catch(() => undefined)}
                      disabled={generatingOpposing}
                      className="rounded-full border border-slate-200 px-3 py-1 text-[10px] font-semibold text-slate-600 hover:border-orange-300 hover:text-orange-600 disabled:opacity-40">
                      {generatingOpposing ? 'Refreshing…' : 'Regenerate'}
                    </button>
                  </div>
                </div>
              ) : openingResponse ? (
                <div className="flex items-center gap-3 text-sm text-slate-500">
                  <LoadingSpinner label="Generating opposing counsel response" />
                </div>
              ) : (
                <Empty text="Submit the opening argument to trigger the opposing response." />
              )}
            </section>

            {/* Rebuttal */}
            <section className="space-y-4 px-7 py-6">
              <div className="flex items-center justify-between">
                <SectionLabel>Rebuttal — Student Advocate</SectionLabel>
                {rebuttalResponse && (
                  <span className="text-[10px] text-slate-800">
                    Round {Math.max(2, safeNumber(rebuttalResponse.round_number ?? rebuttalResponse.current_round, 2))}
                    {rebuttalFlags.length ? ` · ⚠ ${rebuttalFlags.join(', ')}` : ''}
                  </span>
                )}
              </div>

              <textarea
                value={rebuttalArgument}
                onChange={e => setRebuttalArgument(e.target.value)}
                rows={7}
                disabled={!rebuttalReady}
                className="w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm leading-7 text-slate-900 placeholder:text-slate-800 focus:border-orange-300 focus:bg-white focus:outline-none disabled:cursor-not-allowed disabled:opacity-50"
                placeholder={rebuttalReady
                  ? 'Target the objection, preserve the record, respond with discipline.'
                  : 'Awaiting opposing counsel response.'}
              />

              <div className="flex items-center justify-between">
                <button onClick={handleSubmitRebuttal}
                  disabled={!rebuttalReady || submittingRebuttal || generatingJudge}
                  className="rounded-full border border-slate-200 bg-white px-5 py-2 text-sm font-semibold text-slate-800 hover:border-orange-300 hover:bg-orange-50 disabled:opacity-50">
                  {submittingRebuttal ? 'Submitting…' : generatingJudge ? 'Generating evaluation…' : 'Submit Rebuttal'}
                </button>
                <span className="text-xs text-slate-800">{formatNumber(rebuttalArgument.length)} chars</span>
              </div>
            </section>

          </div>
        </div>

        {/* ══ RIGHT PANEL — judge ══════════════════════════════════════════ */}
        <div className="flex flex-1 flex-col overflow-y-auto bg-slate-50">
          <div className="divide-y divide-slate-100">

            {/* Live commentary */}
            <section className="space-y-3 px-6 py-5">
              <SectionLabel>Judge — Live Commentary</SectionLabel>
              <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3">
                <p className="mb-1 text-xs font-semibold uppercase tracking-widest text-amber-500">
                  Stage · {workflowStage}
                </p>
                <p className="text-sm leading-7 text-amber-900">
                  {judgeEvaluation
                    ? safeString(judgeEvaluation.educational_feedback, 'Evaluation complete.')
                    : workflowIndex === 0 ? 'Create the session to establish courtroom context.'
                    : workflowIndex === 1 ? 'Generate the premise to lock the factual record.'
                    : workflowIndex === 2 ? 'Draft the opening with issue–rule–application structure.'
                    : workflowIndex === 3 ? 'Opposing response in flight. Prepare your rebuttal posture.'
                    : workflowIndex === 4 ? 'Keep the rebuttal disciplined and tied to the record.'
                    : 'Review the evaluation and consolidate your learning points.'}
                </p>
              </div>
              <p className="text-xs leading-6 text-slate-500">
                <span className="font-semibold text-slate-600">Burden: </span>
                {judgeEvaluation
                  ? safeString(judgeEvaluation.burden_of_proof_analysis, 'Burden analysis complete.')
                  : 'Keep the burden explicit and tie every assertion to locked facts.'}
              </p>
            </section>

            {/* Final evaluation */}
            <section className="space-y-5 px-6 py-5">
              <div className="flex items-center justify-between">
                <SectionLabel>Final Judge Evaluation</SectionLabel>
                {judgeEvaluation && (
                  <div className="flex items-center gap-2">
                    <button onClick={() => speak(judgeSpeech, 'judge')} disabled={!judgeSpeech}
                      className="rounded-full border border-slate-200 px-3 py-1 text-[10px] font-semibold text-slate-600 hover:border-amber-300 hover:text-amber-700 disabled:opacity-40">
                      ▶ Listen
                    </button>
                    <button onClick={stopSpeech}
                      className="rounded-full border border-slate-200 px-3 py-1 text-[10px] font-semibold text-slate-500 hover:border-slate-300">
                      ■ Stop
                    </button>
                  </div>
                )}
              </div>

              {judgeEvaluation ? (
                <div className="space-y-5">

                  {/* Score strip */}
                  <div className="grid grid-cols-2 gap-3">
                    <ScoreRing score={advocacyScore}  label="Advocacy" />
                    <ScoreRing score={proceduralDisc} label="Procedure" />
                  </div>

                  {/* Final score banner */}
                  <div className="flex items-center justify-between rounded-xl border border-amber-300 bg-gradient-to-r from-amber-50 to-white px-5 py-4">
                    <div>
                      <p className="text-[10px] font-bold uppercase tracking-widest text-amber-500">Final Score</p>
                      <p className="mt-0.5 text-4xl font-black text-slate-900">
                        {Math.round(finalScore)}<span className="text-base font-normal text-slate-800">/100</span>
                      </p>
                    </div>
                    <Badge label="Judgment complete" tone="judgment-complete" />
                  </div>

                  <Divider />

                  {hallucinationPen > 0 && (
                    <JSection title="Hallucination Penalty">
                      <div className="flex items-center gap-3 rounded-xl border border-red-200 bg-red-50 px-4 py-3">
                        <span className="text-2xl font-black text-red-500">−{Math.round(hallucinationPen)}</span>
                        <p className="text-xs text-red-700">Unsupported or speculative content detected.</p>
                      </div>
                    </JSection>
                  )}

                  <JSection title="Procedural Discipline">
                    <ScoreMeter score={proceduralDisc} label="Courtroom discipline score" />
                  </JSection>

                  <Divider />

                  <JSection title="Burden of Proof Analysis">
                    <p className="whitespace-pre-wrap text-sm leading-7 text-slate-700">
                      {safeString(judgeEvaluation.burden_of_proof_analysis, 'No analysis returned.')}
                    </p>
                  </JSection>

                  <JSection title="Evidentiary Sufficiency">
                    <p className="whitespace-pre-wrap text-sm leading-7 text-slate-700">
                      {safeString(judgeEvaluation.evidentiary_sufficiency, 'No analysis returned.')}
                    </p>
                  </JSection>

                  {contradictions.length > 0 && (
                    <JSection title="Contradictions Found">
                      <div className="space-y-1.5">
                        {contradictions.map((item, i) => (
                          <div key={i} className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">{item}</div>
                        ))}
                      </div>
                    </JSection>
                  )}

                  <Divider />

                  <JSection title="Educational Feedback">
                    <p className="whitespace-pre-wrap text-sm leading-7 text-slate-700">
                      {safeString(judgeEvaluation.educational_feedback, 'No feedback returned.')}
                    </p>
                  </JSection>

                  {safeString(judgeEvaluation.termination_recommendation, '') && (
                    <JSection title="Termination Recommendation">
                      <p className="whitespace-pre-wrap text-sm leading-7 text-slate-700">
                        {safeString(judgeEvaluation.termination_recommendation, '')}
                      </p>
                    </JSection>
                  )}

                  {learningPoints.length > 0 && (
                    <JSection title="Learning Points">
                      <div className="grid gap-2 sm:grid-cols-2">
                        {learningPoints.map((pt, i) => (
                          <div key={i} className="rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm leading-6 text-slate-700">{pt}</div>
                        ))}
                      </div>
                    </JSection>
                  )}

                  <button onClick={() => void handleGenerateJudge('manual').catch(() => undefined)}
                    disabled={generatingJudge}
                    className="rounded-full border border-amber-300 bg-amber-50 px-4 py-2 text-xs font-semibold text-amber-700 hover:bg-amber-100 disabled:opacity-50">
                    {generatingJudge ? 'Refreshing…' : 'Regenerate Evaluation'}
                  </button>

                </div>
              ) : (
                <div className="space-y-3">
                  <Empty text="Submit the rebuttal to unlock the final judge analysis and scores." />
                  {rebuttalBusy && <LoadingSpinner label="Generating judge evaluation" />}
                </div>
              )}
            </section>

          </div>
        </div>

      </div>
    </div>
  );
}