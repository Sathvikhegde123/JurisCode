import { api, saveSessionSummary } from './api';
import type {
  ChallengeResponse,
  HealthResponse,
  ModeListResponse,
  ModelsStatusResponse,
  PracticeArgumentResponse,
  PracticeStartResponse,
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
  const response = await api.get<SessionDetailsResponse>(`/practice/session/${sessionId}`);
  return response.data;
}
