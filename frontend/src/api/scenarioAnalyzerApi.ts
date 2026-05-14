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

export async function checkScenarioBackendHealth() {
  return scenarioFetch<unknown>('/health');
}

export function getScenarioApiBaseUrl() {
  return SCENARIO_API.replace(/\/$/, '');
}
