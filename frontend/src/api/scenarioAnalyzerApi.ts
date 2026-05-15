const SCENARIO_API = import.meta.env.VITE_SCENARIO_API_BASE_URL || 'http://localhost:8001';

function isNetworkError(err: unknown): boolean {
  return err instanceof TypeError && String(err.message).toLowerCase().includes('fetch');
}

async function parseJsonResponse<T>(response: Response): Promise<T> {
  const text = await response.text();
  let data: unknown = null;
  if (text) {
    try {
      data = JSON.parse(text) as unknown;
    } catch {
      throw new Error('The scenario service returned an invalid response.');
    }
  }

  if (!response.ok) {
    const record = data && typeof data === 'object' ? (data as Record<string, unknown>) : null;
    const detail =
      (record && typeof record.detail === 'string' && record.detail) ||
      (record && typeof record.message === 'string' && record.message) ||
      response.statusText ||
      'Request failed';
    const err = new Error(detail) as Error & { status?: number };
    err.status = response.status;
    throw err;
  }

  return data as T;
}

async function rawScenarioFetch(path: string, init?: RequestInit): Promise<Response> {
  const url = `${SCENARIO_API.replace(/\/$/, '')}${path}`;
  const method = (init?.method ?? 'GET').toUpperCase();
  const withJsonBody = method !== 'GET' && method !== 'HEAD';
  try {
    return await fetch(url, {
      ...init,
      headers: {
        Accept: 'application/json',
        ...(withJsonBody ? { 'Content-Type': 'application/json' } : {}),
        ...(init?.headers as Record<string, string>),
      },
    });
  } catch (e) {
    if (isNetworkError(e)) {
      throw new Error(
        'Scenario Analyzer backend is not reachable. Please make sure it is running on port 8001.',
      );
    }
    throw e;
  }
}

async function scenarioFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await rawScenarioFetch(path, init);
  return parseJsonResponse<T>(response);
}

export type AnalyzePayload = {
  scenario: string;
  user_context?: {
    state: string;
    language: string;
  };
};

export async function analyzeScenario(payload: AnalyzePayload) {
  return scenarioFetch<unknown>('/api/scenario/analyze', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function getFullReport(sessionId: string) {
  return scenarioFetch<unknown>(`/api/scenario/report/${encodeURIComponent(sessionId)}`);
}

export type ChatPayload = {
  session_id: string;
  message: string;
};

export async function continueScenarioChat(payload: ChatPayload) {
  return scenarioFetch<unknown>('/api/scenario/chat', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function getChatHistory(sessionId: string) {
  return scenarioFetch<unknown>(`/api/scenario/chat/${encodeURIComponent(sessionId)}`);
}

/** Returns null if session or history is missing (HTTP 404). */
export async function getChatHistoryOrNull(sessionId: string): Promise<unknown | null> {
  const response = await rawScenarioFetch(`/api/scenario/chat/${encodeURIComponent(sessionId)}`, {
    method: 'GET',
  });
  if (response.status === 404) {
    return null;
  }
  return parseJsonResponse<unknown>(response);
}

export type ScenarioSessionListItem = {
  session_id: string;
  original_scenario: string;
  issue_type: string;
  source_pack_used: string;
  created_at: string;
};

export type ScenarioSessionsResponse = {
  sessions: ScenarioSessionListItem[];
};

/** Non-dev backends may return 404 for this route; yields empty list without throwing. */
export async function listScenarioSessions(): Promise<ScenarioSessionsResponse> {
  const response = await rawScenarioFetch('/api/scenario/sessions', { method: 'GET' });
  if (response.status === 404) {
    return { sessions: [] };
  }
  return parseJsonResponse<ScenarioSessionsResponse>(response);
}

export async function getSourcePacks() {
  return scenarioFetch<unknown>('/api/scenario/source-packs');
}

export type ClarityCategoryBlock = {
  score: number;
  max_score: number;
  reason: string;
  sub_scores: Record<string, number>;
};

export type LegalClarityScoreResponse = {
  session_id: string;
  legal_clarity_score: number;
  clarity_level: string;
  score_breakdown: {
    issue_understanding: ClarityCategoryBlock;
    fact_clarity: ClarityCategoryBlock;
    document_clarity: ClarityCategoryBlock;
    risk_clarity: ClarityCategoryBlock;
  };
  strengths: string[];
  remaining_gaps: string[];
  summary_feedback: string;
  teacher_explanation: string;
};

function parseLegalClarityScore(data: unknown): LegalClarityScoreResponse | null {
  if (!data || typeof data !== 'object') {
    return null;
  }
  const o = data as Record<string, unknown>;
  const session_id = typeof o.session_id === 'string' ? o.session_id : '';
  if (!session_id) {
    return null;
  }
  const breakdown = o.score_breakdown;
  if (!breakdown || typeof breakdown !== 'object') {
    return null;
  }
  const b = breakdown as Record<string, unknown>;
  const pickBlock = (k: string): ClarityCategoryBlock => {
    const raw = b[k];
    if (!raw || typeof raw !== 'object') {
      return { score: 0, max_score: 0, reason: '', sub_scores: {} };
    }
    const blk = raw as Record<string, unknown>;
    const subs = blk.sub_scores && typeof blk.sub_scores === 'object' ? (blk.sub_scores as Record<string, unknown>) : {};
    const sub_scores: Record<string, number> = {};
    for (const [sk, sv] of Object.entries(subs)) {
      const n = typeof sv === 'number' ? sv : Number(sv);
      sub_scores[sk] = Number.isFinite(n) ? n : 0;
    }
    return {
      score: typeof blk.score === 'number' ? blk.score : Number(blk.score) || 0,
      max_score: typeof blk.max_score === 'number' ? blk.max_score : Number(blk.max_score) || 0,
      reason: typeof blk.reason === 'string' ? blk.reason : '',
      sub_scores,
    };
  };
  const strengths = Array.isArray(o.strengths) ? o.strengths.filter((x): x is string => typeof x === 'string') : [];
  const gaps = Array.isArray(o.remaining_gaps)
    ? o.remaining_gaps.filter((x): x is string => typeof x === 'string')
    : [];
  return {
    session_id,
    legal_clarity_score: typeof o.legal_clarity_score === 'number' ? o.legal_clarity_score : Number(o.legal_clarity_score) || 0,
    clarity_level: typeof o.clarity_level === 'string' ? o.clarity_level : '',
    score_breakdown: {
      issue_understanding: pickBlock('issue_understanding'),
      fact_clarity: pickBlock('fact_clarity'),
      document_clarity: pickBlock('document_clarity'),
      risk_clarity: pickBlock('risk_clarity'),
    },
    strengths,
    remaining_gaps: gaps,
    summary_feedback: typeof o.summary_feedback === 'string' ? o.summary_feedback : '',
    teacher_explanation: typeof o.teacher_explanation === 'string' ? o.teacher_explanation : '',
  };
}

export async function generateLegalClarityScore(sessionId: string): Promise<LegalClarityScoreResponse> {
  const response = await rawScenarioFetch(`/api/scenario/score/${encodeURIComponent(sessionId)}`, {
    method: 'POST',
  });
  const text = await response.text();
  let data: unknown = null;
  if (text) {
    try {
      data = JSON.parse(text) as unknown;
    } catch {
      throw new Error('The scenario service returned an invalid response for clarity scoring.');
    }
  }
  if (!response.ok) {
    const record = data && typeof data === 'object' ? (data as Record<string, unknown>) : null;
    const detail =
      (record && typeof record.detail === 'string' && record.detail) ||
      (record && typeof record.message === 'string' && record.message) ||
      response.statusText ||
      'Could not generate clarity score';
    throw new Error(detail);
  }
  const parsed = parseLegalClarityScore(data);
  if (!parsed) {
    throw new Error('Could not parse clarity score response.');
  }
  return parsed;
}

/** Returns null if no score exists (HTTP 404) or session is unknown. */
export async function getLegalClarityScore(sessionId: string): Promise<LegalClarityScoreResponse | null> {
  const response = await rawScenarioFetch(`/api/scenario/score/${encodeURIComponent(sessionId)}`, {
    method: 'GET',
  });
  const text = await response.text();
  if (response.status === 404) {
    return null;
  }
  let data: unknown = null;
  if (text) {
    try {
      data = JSON.parse(text) as unknown;
    } catch {
      throw new Error('The scenario service returned an invalid response when loading clarity score.');
    }
  }
  if (!response.ok) {
    const record = data && typeof data === 'object' ? (data as Record<string, unknown>) : null;
    const detail =
      (record && typeof record.detail === 'string' && record.detail) ||
      (record && typeof record.message === 'string' && record.message) ||
      response.statusText ||
      'Could not load clarity score';
    throw new Error(detail);
  }
  return parseLegalClarityScore(data);
}

export async function checkScenarioBackendHealth() {
  return scenarioFetch<unknown>('/health');
}

export function getScenarioApiBaseUrl() {
  return SCENARIO_API.replace(/\/$/, '');
}
