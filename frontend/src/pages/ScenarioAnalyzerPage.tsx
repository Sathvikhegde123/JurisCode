import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  analyzeScenario,
  continueScenarioChat,
  generateLegalClarityScore,
  getFullReport,
  getChatHistoryOrNull,
  getLegalClarityScore,
  listScenarioSessions,
  checkScenarioBackendHealth,
  type LegalClarityScoreResponse,
  type ScenarioSessionListItem,
} from '@/api/scenarioAnalyzerApi';
import { GlassCard } from '@/components/common/GlassCard';
import { CompactReportView } from '@/components/scenarioAnalyzer/CompactReportView';
import { FullReportModal } from '@/components/scenarioAnalyzer/FullReportModal';
import { ScenarioInputCard } from '@/components/scenarioAnalyzer/ScenarioInputCard';
import { ScenarioLoadingState } from '@/components/scenarioAnalyzer/ScenarioLoadingState';
import { ScenarioSessionSidebar } from '@/components/scenarioAnalyzer/ScenarioSessionSidebar';
import { LegalClarityScoreCard } from '@/components/scenarioAnalyzer/LegalClarityScoreCard';
import { SocraticChatPanel, type ChatMessageVM } from '@/components/scenarioAnalyzer/SocraticChatPanel';
import { clearScenarioSessionId, getScenarioSessionId, setScenarioSessionId } from '@/utils/scenarioSession';
import { deriveCompactFromFullReport, type CompactViewShape, type LawyerWarningShape } from '@/utils/scenarioReportMapping';
import {
  buildSituationOverview,
  isLimitedFullReport,
  polishMainPoints,
  polishNextSteps,
} from '@/utils/scenarioCompactDisplay';
import { getFirstSocraticQuestion } from '@/utils/scenarioSocratic';
import { wait } from '@/utils/wait';

function isRecord(v: unknown): v is Record<string, unknown> {
  return typeof v === 'object' && v !== null && !Array.isArray(v);
}

function parseLawyerWarning(v: unknown): LawyerWarningShape {
  if (!isRecord(v)) {
    return { required: false, reason: '' };
  }
  return {
    required: v.required === true,
    reason: typeof v.reason === 'string' ? v.reason : '',
  };
}

function asStringList(v: unknown): string[] {
  if (!Array.isArray(v)) {
    return [];
  }
  return v.filter((x): x is string => typeof x === 'string');
}

function parseCompactFromAnalyzePayload(data: unknown): {
  sessionId: string;
  compact: CompactViewShape;
  suggested: string[];
  issueType: string;
} | null {
  if (!isRecord(data)) {
    return null;
  }
  const sessionId = typeof data.session_id === 'string' ? data.session_id : '';
  if (!sessionId) {
    return null;
  }
  const issueType = typeof data.issue_type === 'string' ? data.issue_type : '';
  const cv = data.compact_view;
  if (!isRecord(cv)) {
    return null;
  }
  const compact: CompactViewShape = {
    detected_issue: typeof cv.detected_issue === 'string' ? cv.detected_issue : '',
    short_summary: typeof cv.short_summary === 'string' ? cv.short_summary : '',
    main_points: asStringList(cv.main_points),
    recommended_next_steps: asStringList(cv.recommended_next_steps),
    lawyer_warning: parseLawyerWarning(cv.lawyer_warning),
    confidence: typeof cv.confidence === 'string' ? cv.confidence : '',
    disclaimer:
      typeof cv.disclaimer === 'string'
        ? cv.disclaimer
        : 'This is legal information for awareness and education, not legal advice.',
  };
  const suggested = asStringList(data.suggested_follow_up_questions);
  return { sessionId, compact, suggested, issueType };
}

function parseChatHistoryPayload(data: unknown): ChatMessageVM[] {
  if (!isRecord(data)) {
    return [];
  }
  const messages = data.messages;
  if (!Array.isArray(messages)) {
    return [];
  }
  const out: ChatMessageVM[] = [];
  for (const m of messages) {
    if (!isRecord(m)) {
      continue;
    }
    const role = m.role === 'user' ? 'user' : 'assistant';
    const content = typeof m.content === 'string' ? m.content : '';
    const created_at = typeof m.created_at === 'string' ? m.created_at : undefined;
    const row: ChatMessageVM = { role, content };
    if (created_at) {
      row.created_at = created_at;
    }
    out.push(row);
  }
  return out;
}

function parseChatPostPayload(data: unknown) {
  if (!isRecord(data)) {
    return null;
  }
  const assistant_message = typeof data.assistant_message === 'string' ? data.assistant_message : '';
  const session_id = typeof data.session_id === 'string' ? data.session_id : '';
  return {
    session_id,
    assistant_message,
    updated_understanding: asStringList(data.updated_understanding),
    recommended_next_steps: asStringList(data.recommended_next_steps),
    lawyer_warning: parseLawyerWarning(data.lawyer_warning),
    disclaimer: typeof data.disclaimer === 'string' ? data.disclaimer : '',
  };
}

export function ScenarioAnalyzerPage() {
  const [scenario, setScenario] = useState('');

  const [sessionId, setSessionId] = useState<string | null>(() => getScenarioSessionId());
  const [sessions, setSessions] = useState<ScenarioSessionListItem[]>([]);
  const [sessionsListError, setSessionsListError] = useState('');

  const [compactView, setCompactView] = useState<CompactViewShape | null>(null);
  const [suggestedQuestions, setSuggestedQuestions] = useState<string[]>([]);
  const [issueType, setIssueType] = useState('');

  const [messages, setMessages] = useState<ChatMessageVM[]>([]);
  const [mode, setMode] = useState<'input' | 'report' | 'chat'>('input');

  const [loading, setLoading] = useState(false);
  const [loadingStep, setLoadingStep] = useState(0);
  const [chatLoading, setChatLoading] = useState(false);
  const [reportLoading, setReportLoading] = useState(false);
  const [error, setError] = useState('');

  const [chatInput, setChatInput] = useState('');

  const [reportModalOpen, setReportModalOpen] = useState(false);
  const [modalReportBody, setModalReportBody] = useState<Record<string, unknown> | null>(null);

  const [backendOnline, setBackendOnline] = useState<boolean | null>(null);
  const [mobileSessionsOpen, setMobileSessionsOpen] = useState(false);
  const [restorePrompt, setRestorePrompt] = useState<ChatMessageVM[] | null>(null);

  const [legalClarityScore, setLegalClarityScore] = useState<LegalClarityScoreResponse | null>(null);
  const [scoreLoading, setScoreLoading] = useState(false);

  const loadScoreForSession = useCallback(async (sid: string | null) => {
    if (!sid) {
      setLegalClarityScore(null);
      return;
    }
    try {
      const s = await getLegalClarityScore(sid);
      setLegalClarityScore(s);
    } catch {
      setLegalClarityScore(null);
    }
  }, []);

  const refreshSessions = useCallback(async (): Promise<ScenarioSessionListItem[]> => {
    try {
      const data = await listScenarioSessions();
      const next = data.sessions ?? [];
      setSessions(next);
      setSessionsListError('');
      return next;
    } catch {
      setSessions([]);
      setSessionsListError('Could not load previous sessions.');
      return [];
    }
  }, []);

  const resetWorkspace = useCallback(() => {
    clearScenarioSessionId();
    setSessionId(null);
    setCompactView(null);
    setSuggestedQuestions([]);
    setIssueType('');
    setMessages([]);
    setScenario('');
    setMode('input');
    setError('');
    setChatInput('');
    setRestorePrompt(null);
    setModalReportBody(null);
    setReportModalOpen(false);
    setLegalClarityScore(null);
    setScoreLoading(false);
  }, []);

  const reportDisplay = useMemo(() => {
    if (!compactView) {
      return null;
    }
    const situationOverview = buildSituationOverview(compactView, scenario.trim());
    const keyPoints = polishMainPoints(compactView.main_points, scenario);
    const practicalNextSteps = polishNextSteps(compactView.recommended_next_steps);
    return { situationOverview, keyPoints, practicalNextSteps };
  }, [compactView, scenario]);

  const hasUserChatAnswer = useMemo(() => messages.some((m) => m.role === 'user'), [messages]);

  useEffect(() => {
    let cancelled = false;

    (async () => {
      try {
        await checkScenarioBackendHealth();
        if (!cancelled) {
          setBackendOnline(true);
        }
      } catch {
        if (!cancelled) {
          setBackendOnline(false);
        }
      }

      const loaded = await refreshSessions();

      const sid = getScenarioSessionId();
      if (!sid || cancelled) {
        return;
      }
      setSessionId(sid);

      const match = loaded.find((x) => x.session_id === sid);
      if (match && !cancelled) {
        setScenario(match.original_scenario);
        setIssueType(match.source_pack_used || match.issue_type || '');
      }

      const hist = await getChatHistoryOrNull(sid);
      if (cancelled) {
        return;
      }
      if (hist === null) {
        clearScenarioSessionId();
        setSessionId(null);
        return;
      }
      const restored = parseChatHistoryPayload(hist);
      if (restored.length > 0) {
        setRestorePrompt(restored);
        return;
      }

      try {
        const raw = await getFullReport(sid);
        if (cancelled) {
          return;
        }
        if (!isRecord(raw)) {
          throw new Error('bad');
        }
        const fr = raw.full_report;
        const reportObj = isRecord(fr) ? fr : {};
        setCompactView(deriveCompactFromFullReport(reportObj));
        setSuggestedQuestions([]);
        setIssueType(
          match?.source_pack_used ||
            match?.issue_type ||
            (typeof reportObj.issue_type === 'string' ? reportObj.issue_type : '') ||
            (typeof reportObj.source_pack_used === 'string' ? reportObj.source_pack_used : '') ||
            '',
        );
        setMode('report');
        if (!cancelled) {
          await loadScoreForSession(sid);
        }
      } catch (e) {
        const st = typeof e === 'object' && e !== null && 'status' in e ? Number((e as { status: number }).status) : undefined;
        if (st === 404) {
          clearScenarioSessionId();
          setSessionId(null);
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [refreshSessions, loadScoreForSession]);

  useEffect(() => {
    if (!loading) {
      setLoadingStep(0);
      return;
    }
    const id = setInterval(() => {
      setLoadingStep((s) => Math.min(s + 1, 2));
    }, 1400);
    return () => clearInterval(id);
  }, [loading]);

  const handleAnalyze = async () => {
    setError('');
    setLegalClarityScore(null);
    setScoreLoading(false);
    setLoading(true);
    try {
      const raw = await Promise.all([
        analyzeScenario({
          scenario: scenario.trim(),
          user_context: { state: 'Unknown', language: 'English' },
        }),
        wait(3000),
      ]).then(([r]) => r);

      const parsed = parseCompactFromAnalyzePayload(raw);
      if (!parsed) {
        throw new Error('Invalid response from analyzer.');
      }
      setScenarioSessionId(parsed.sessionId);
      setSessionId(parsed.sessionId);
      setCompactView(parsed.compact);
      setSuggestedQuestions(parsed.suggested);
      setIssueType(parsed.issueType);
      setMode('report');
      setBackendOnline(true);
      const loaded = await refreshSessions();
      const row = loaded.find((x) => x.session_id === parsed.sessionId);
      if (row?.source_pack_used || row?.issue_type) {
        setIssueType(row.source_pack_used || row.issue_type || parsed.issueType);
      }
    } catch (e) {
      const msg = e instanceof Error ? e.message : '';
      if (msg.includes('not reachable')) {
        setError('Could not analyze this scenario. Make sure the Scenario Analyzer backend is running on port 8001.');
        setBackendOnline(false);
      } else {
        setError('Could not analyze this scenario right now. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  const openFullReportModal = async () => {
    if (!sessionId) {
      return;
    }
    setReportModalOpen(true);
    setReportLoading(true);
    setModalReportBody(null);
    try {
      const raw = await getFullReport(sessionId);
      if (!isRecord(raw)) {
        throw new Error('Bad report payload');
      }
      const fr = raw.full_report;
      setModalReportBody(isRecord(fr) ? fr : {});
    } catch {
      setModalReportBody(null);
      setError('Could not load full report.');
    } finally {
      setReportLoading(false);
    }
  };

  const handleContinueChat = () => {
    if (!compactView) {
      return;
    }
    setLegalClarityScore(null);
    setScoreLoading(false);
    const pack =
      issueType ||
      sessions.find((x) => x.session_id === sessionId)?.source_pack_used ||
      sessions.find((x) => x.session_id === sessionId)?.issue_type ||
      '';
    const first = getFirstSocraticQuestion({
      issueType: pack,
      detectedIssue: compactView.detected_issue,
      suggestedQuestions,
    });
    setMessages([
      {
        role: 'assistant',
        content: `I'll help narrow this down step by step. ${first}`,
        created_at: new Date().toISOString(),
      },
    ]);
    setMode('chat');
  };

  const handleSendChat = async () => {
    const text = chatInput.trim();
    if (!sessionId || !text || chatLoading) {
      return;
    }
    const userMsg: ChatMessageVM = { role: 'user', content: text, created_at: new Date().toISOString() };
    setMessages((m) => [...m, userMsg]);
    setChatInput('');
    setChatLoading(true);
    try {
      const raw = await continueScenarioChat({ session_id: sessionId, message: text });
      const parsed = parseChatPostPayload(raw);
      if (!parsed || !parsed.assistant_message) {
        throw new Error('Bad chat payload');
      }
      const assistant: ChatMessageVM = {
        role: 'assistant',
        content: parsed.assistant_message,
        created_at: new Date().toISOString(),
        metadata: {
          updated_understanding: parsed.updated_understanding,
          recommended_next_steps: parsed.recommended_next_steps.slice(0, 3),
          lawyer_warning: parsed.lawyer_warning,
        },
      };
      setMessages((m) => [...m, assistant]);
      setBackendOnline(true);
    } catch {
      setMessages((m) => [
        ...m,
        {
          role: 'assistant',
          content: 'Could not continue the conversation. Please try again.',
          created_at: new Date().toISOString(),
        },
      ]);
    } finally {
      setChatLoading(false);
    }
  };

  const handleGenerateClarityScore = async () => {
    if (!sessionId) {
      return;
    }
    setError('');
    setScoreLoading(true);
    try {
      const s = await generateLegalClarityScore(sessionId);
      setLegalClarityScore(s);
      setBackendOnline(true);
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Could not generate clarity score.';
      setError(msg);
    } finally {
      setScoreLoading(false);
    }
  };

  const handleSelectSession = async (s: ScenarioSessionListItem) => {
    setError('');
    setScenarioSessionId(s.session_id);
    setSessionId(s.session_id);
    setScenario(s.original_scenario);

    const hist = await getChatHistoryOrNull(s.session_id);
    if (hist === null) {
      clearScenarioSessionId();
      setSessionId(null);
      await loadScoreForSession(null);
      return;
    }
    const restored = parseChatHistoryPayload(hist);
    if (restored.length > 0) {
      setCompactView(null);
      setSuggestedQuestions([]);
      setIssueType(s.source_pack_used || s.issue_type || '');
      setMessages(restored);
      setMode('chat');
      await loadScoreForSession(s.session_id);
      return;
    }

    try {
      const raw = await getFullReport(s.session_id);
      if (!isRecord(raw)) {
        throw new Error('bad');
      }
      const fr = raw.full_report;
      const reportObj = isRecord(fr) ? fr : {};
      setCompactView(deriveCompactFromFullReport(reportObj));
      setSuggestedQuestions([]);
      setIssueType(s.source_pack_used || s.issue_type || '');
      setMessages([]);
      setMode('report');
      await loadScoreForSession(s.session_id);
    } catch {
      setMode('input');
      setError('Could not load this session. Starting fresh is easiest.');
      await loadScoreForSession(null);
    }
  };

  return (
    <div className="space-y-6 p-4 pb-24 sm:p-6 xl:pb-6">
      <div className="flex flex-col gap-6 xl:flex-row xl:items-start">
        <ScenarioSessionSidebar
          sessions={sessions}
          selectedSessionId={sessionId}
          sessionsError={sessionsListError}
          mobileOpen={mobileSessionsOpen}
          onMobileOpenChange={setMobileSessionsOpen}
          onSelectSession={handleSelectSession}
          onNewScenario={resetWorkspace}
        />

        <div className="min-w-0 flex-1 space-y-4">
          {backendOnline === true ? (
            <p className="text-xs font-medium uppercase tracking-wide text-emeraldGlow">Scenario service online</p>
          ) : null}

          {restorePrompt ? (
            <GlassCard title="Continue previous conversation?" subtitle="We found chat history for this browser session.">
              <div className="flex flex-wrap gap-3">
                <button
                  type="button"
                  className="rounded-full bg-electric px-5 py-2.5 text-sm font-semibold text-white hover:brightness-110"
                  onClick={() => {
                    setMessages(restorePrompt);
                    setMode('chat');
                    setRestorePrompt(null);
                    void loadScoreForSession(sessionId);
                  }}
                >
                  Continue
                </button>
                <button
                  type="button"
                  className="rounded-full border border-amber-200/80 bg-white px-5 py-2.5 text-sm font-semibold text-slate-900 hover:border-electric/40"
                  onClick={() => {
                    resetWorkspace();
                  }}
                >
                  Start new
                </button>
              </div>
            </GlassCard>
          ) : null}

          {error ? (
            <div className="rounded-2xl border border-red-200/80 bg-red-50/90 px-4 py-3 text-sm text-red-950">{error}</div>
          ) : null}

          {mode === 'input' && !restorePrompt ? (
            <>
              {loading ? <ScenarioLoadingState stepIndex={loadingStep} /> : null}
              {!loading ? (
                <ScenarioInputCard
                  scenario={scenario}
                  onScenarioChange={setScenario}
                  onAnalyze={handleAnalyze}
                  loading={loading}
                  backendOnline={backendOnline}
                />
              ) : null}
            </>
          ) : null}

          {mode === 'report' && compactView && reportDisplay ? (
            <CompactReportView
              detectedIssue={compactView.detected_issue}
              situationOverview={reportDisplay.situationOverview}
              keyPoints={reportDisplay.keyPoints}
              practicalNextSteps={reportDisplay.practicalNextSteps}
              onContinueChat={handleContinueChat}
              onFullReport={openFullReportModal}
              onNewScenario={resetWorkspace}
            />
          ) : null}

          {mode === 'chat' ? (
            <SocraticChatPanel
              messages={messages}
              chatInput={chatInput}
              onChatInputChange={setChatInput}
              onSend={handleSendChat}
              chatLoading={chatLoading}
            />
          ) : null}

          {mode === 'chat' && sessionId ? (
            <div className="rounded-3xl border border-amber-200/70 bg-white/95 p-4 shadow-sm">
              <button
                type="button"
                disabled={scoreLoading || !hasUserChatAnswer}
                onClick={handleGenerateClarityScore}
                className="w-full rounded-full bg-electric px-5 py-2.5 text-sm font-semibold text-white transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-50 sm:w-auto"
              >
                Finish & Generate Clarity Score
              </button>
              {!hasUserChatAnswer ? (
                <p className="mt-2 text-xs text-slate-600">
                  Answer at least one follow-up question before generating clarity score.
                </p>
              ) : null}
              {scoreLoading ? (
                <p className="mt-3 text-sm text-slate-700">Evaluating conversation clarity...</p>
              ) : null}
            </div>
          ) : null}

          {legalClarityScore && sessionId && legalClarityScore.session_id === sessionId ? (
            <LegalClarityScoreCard score={legalClarityScore} />
          ) : null}

          {mode === 'chat' ? (
            <div className="flex flex-wrap gap-3">
              <button
                type="button"
                onClick={openFullReportModal}
                className="rounded-full border border-amber-200/80 bg-white px-5 py-2 text-sm font-semibold text-slate-900 hover:border-electric/40"
              >
                View full report
              </button>
              <button
                type="button"
                onClick={resetWorkspace}
                className="rounded-full border border-slate-200 bg-white px-5 py-2 text-sm font-semibold text-slate-700 hover:border-slate-300"
              >
                New scenario
              </button>
            </div>
          ) : null}
        </div>
      </div>

      <FullReportModal
        open={reportModalOpen}
        loading={reportLoading}
        fullReport={modalReportBody}
        limitedBanner={modalReportBody ? isLimitedFullReport(modalReportBody) : false}
        onClose={() => setReportModalOpen(false)}
        onContinueChat={() => setMode('chat')}
      />
    </div>
  );
}
