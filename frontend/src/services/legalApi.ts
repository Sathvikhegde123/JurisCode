import { api, loadSessionSummaries, saveSessionSummary } from './api';
import type {
  ChallengeResponse,
  HealthResponse,
  ModeListResponse,
  ModelsStatusResponse,
  PracticeJudgeEvaluationResponse,
  PracticeOpposingResponse,
  PracticePremiseResponse,
  PracticeArgumentResponse,
  PracticeSessionResponse,
  PracticeStartResponse,
  PracticeWorkflowArgumentResponse,
  SessionDetailsResponse,
  TopicListResponse,
} from '@/types';
import { clamp, safeNumber, safeString } from '@/utils/format';

function pickString(data: unknown, keys: string[], fallback = '') {
  if (!data || typeof data !== 'object') {
    return fallback;
  }

  const record = data as Record<string, unknown>;
  for (const key of keys) {
    const value = record[key];
    if (typeof value === 'string' && value.trim()) {
      return value;
    }
  }

  return fallback;
}

function pickArray(data: unknown, keys: string[]) {
  if (!data || typeof data !== 'object') {
    return [] as string[];
  }

  const record = data as Record<string, unknown>;
  for (const key of keys) {
    const value = record[key];
    if (Array.isArray(value)) {
      return value.filter((item): item is string => typeof item === 'string');
    }
  }

  return [] as string[];
}

function pickRecord(data: unknown, keys: string[]) {
  if (!data || typeof data !== 'object') {
    return {} as Record<string, unknown>;
  }

  const record = data as Record<string, unknown>;
  for (const key of keys) {
    const value = record[key];
    if (value && typeof value === 'object' && !Array.isArray(value)) {
      return value as Record<string, unknown>;
    }
  }

  return {} as Record<string, unknown>;
}

export async function getHealth() {
  const response = await api.get<HealthResponse>('/health');
  return response.data;
}

export async function getModelsStatus() {
  const response = await api.get<ModelsStatusResponse>('/models/status');
  return response.data;
}

export async function getPremiseTopics() {
  const response = await api.get<TopicListResponse>('/premise/topics');
  return response.data.topics ?? [];
}

export async function getPremiseModes() {
  const response = await api.get<ModeListResponse>('/premise/modes');
  return response.data.modes ?? [];
}

function stringifyPremise(premise: unknown) {
  if (typeof premise === 'string') {
    return premise;
  }

  if (!premise || typeof premise !== 'object') {
    return 'Premise generated.';
  }

  const record = premise as Record<string, unknown>;
  return safeString(
    record.summary ?? record.description ?? record.text ?? record.narrative,
    JSON.stringify(record, null, 2),
  );
}

function saveWorkflowSummary(payload: {
  session_id: string;
  topic?: string;
  mode?: string;
  premise?: unknown;
  workflowStage?: string;
  status?: string;
  latestScore?: number;
  latestFeedback?: string;
}) {
  const existing = loadSessionSummaries().find((session) => session.session_id === payload.session_id);

  saveSessionSummary({
    session_id: payload.session_id,
    topic: safeString(payload.topic, existing?.topic ?? 'Practice session'),
    mode: safeString(payload.mode, existing?.mode ?? 'Practice arena'),
    premise: stringifyPremise(payload.premise ?? existing?.premise),
    createdAt: existing?.createdAt ?? new Date().toISOString(),
    workflowStage: payload.workflowStage ?? existing?.workflowStage,
    status: payload.status ?? existing?.status,
    latestScore: payload.latestScore ?? existing?.latestScore,
    latestFeedback: payload.latestFeedback ?? existing?.latestFeedback,
  });
}

export async function createPracticeSession(payload: { topic?: string; mode?: string; randomize?: boolean }) {
  const response = await api.post<PracticeSessionResponse>('/api/v1/sessions', payload);
  const data = response.data;
  const record = data as Record<string, unknown>;
  const sessionId = safeString(data.session_id ?? record.id, '');
  if (!sessionId) {
    throw new Error('Session creation failed: backend did not return a session_id.');
  }
  const topic = safeString(data.topic, payload.topic ?? 'Courtroom practice');
  const mode = safeString(data.mode, payload.mode ?? 'Practice arena');
  const workflowStage = safeString(data.workflow_stage, 'session-created');
  const status = safeString(data.session_status ?? record.status, 'active');

  saveWorkflowSummary({
    session_id: sessionId,
    topic,
    mode,
    workflowStage,
    status,
    premise: 'Session initialized. Generate the premise to continue.',
  });

  return {
    ...data,
    session_id: sessionId,
    topic,
    mode,
    workflow_stage: workflowStage,
    session_status: status,
  };
}

export async function generatePracticePremise(payload: { sessionId: string; topic: string; mode: string }) {
  const response = await api.post<PracticePremiseResponse>(`/api/v1/sessions/${payload.sessionId}/premise`, {
    topic: payload.topic,
    mode: payload.mode,
  });
  const data = response.data;
  const workflowStage = safeString(data.workflow_stage, 'premise-generated');
  const record = data as Record<string, unknown>;
  const status = safeString(data.session_status ?? record.status, 'awaiting-opening');

  saveWorkflowSummary({
    session_id: safeString(data.session_id, payload.sessionId),
    premise: data.premise,
    workflowStage,
    status,
    latestFeedback: safeString(data.legal_issue_summary, 'Premise generated.'),
  });

  return {
    ...data,
    session_id: safeString(data.session_id, payload.sessionId),
    workflow_stage: workflowStage,
    session_status: status,
  };
}

export async function submitOpeningArgument(payload: { sessionId: string; content: string }) {
  const response = await api.post<PracticeWorkflowArgumentResponse>(`/api/v1/sessions/${payload.sessionId}/opening`, {
    content: payload.content,
  });

  return response.data;
}

export async function generateOpposingCounselResponse(sessionId: string) {
  const response = await api.post<PracticeOpposingResponse>(`/api/v1/sessions/${sessionId}/opposing`, {});
  return response.data;
}

export async function submitRebuttalArgument(payload: { sessionId: string; content: string }) {
  const response = await api.post<PracticeWorkflowArgumentResponse>(`/api/v1/sessions/${payload.sessionId}/rebuttal`, {
    content: payload.content,
  });

  return response.data;
}

export async function generateJudgeEvaluation(sessionId: string) {
  const response = await api.post<PracticeJudgeEvaluationResponse>(`/api/v1/sessions/${sessionId}/judge`, {});
  const data = response.data;

  saveWorkflowSummary({
    session_id: safeString(data.session_id, sessionId),
    premise: 'Judge evaluation completed.',
    workflowStage: safeString(data.workflow_stage, 'judgment-complete'),
    status: safeString(data.session_status, 'judgment-complete'),
    latestScore: clamp(safeNumber(data.final_score, 0), 0, 100),
    latestFeedback: safeString(data.educational_feedback, 'Final evaluation complete.'),
  });

  return {
    ...data,
    workflow_stage: safeString(data.workflow_stage, 'judgment-complete'),
    session_status: safeString(data.session_status, 'judgment-complete'),
  };
}

export async function startPractice(payload: { topic?: string; mode?: string; randomize?: boolean }) {
  const response = await api.post<PracticeStartResponse>('/practice/start', payload);
  const data = response.data;
  const sessionId = safeString(data.session_id, crypto.randomUUID());
  const topic = safeString(data.topic, payload.topic ?? 'General legal reasoning');
  const mode = safeString(data.mode, payload.mode ?? 'mock trial practice');
  const premise = safeString(data.premise, 'Your scenario will appear here once the backend responds.');

  saveSessionSummary({
    session_id: sessionId,
    topic,
    mode,
    premise,
    createdAt: new Date().toISOString(),
  });

  return { ...data, session_id: sessionId, topic, mode, premise };
}

export async function submitPracticeArgument(payload: { sessionId: string; userArgument: string }) {
  const response = await api.post<PracticeArgumentResponse>('/practice/argument', {
    session_id: payload.sessionId,
    user_argument: payload.userArgument,
  });

  const data = response.data;
  const objectionFeedback = pickRecord(data, ['objection_feedback', 'feedback', 'analysis']);
  const score = clamp(safeNumber(objectionFeedback.argument_strength_score ?? data.score, 62), 0, 100);
  const opposingResponse = pickString(data, ['opposing_response', 'opposition', 'challenge_response'], 'The opposing counsel response will appear here.');

  saveSessionSummary({
    session_id: payload.sessionId,
    topic: safeString(data.topic, 'Practice session'),
    mode: safeString(data.mode, 'Practice arena'),
    premise: safeString(data.premise, 'Courtroom premise in progress'),
    createdAt: new Date().toISOString(),
    latestScore: score,
    latestFeedback: safeString(objectionFeedback.summary, pickString(data, ['summary'], 'Argument analyzed.')),
  });

  return {
    ...data,
    opposing_response: opposingResponse,
    objection_feedback: objectionFeedback,
    score,
  };
}

export async function challengeArgument(payload: { premise: string; userArgument: string; sessionId?: string }) {
  const response = await api.post<ChallengeResponse>('/opposing/challenge', {
    premise: payload.premise,
    user_argument: payload.userArgument,
    session_id: payload.sessionId,
  });

  const data = response.data;
  return {
    ...data,
    opposing_response: pickString(data, ['opposing_response', 'response', 'challenge'], 'No opposing counsel response was returned.'),
    statutory_citations: pickArray(data, ['statutory_citations', 'citations', 'authority']),
    socratic_questions: pickArray(data, ['socratic_questions', 'questions', 'follow_up_questions']),
    metadata: pickRecord(data, ['metadata']),
  };
}

export async function getPracticeSession(sessionId: string) {
  const response = await api.get<SessionDetailsResponse>(`/api/v1/sessions/${sessionId}`);
  return response.data;
}
