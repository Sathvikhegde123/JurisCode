import axios from 'axios';

export const api = axios.create({
  baseURL:
    import.meta.env.VITE_API_BASE_URL ?? `${window.location.protocol}//${window.location.hostname}:8000`,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

export type ApiError = {
  message: string;
  status?: number;
};

export function getApiError(error: unknown): ApiError {
  if (axios.isAxiosError(error)) {
    return {
      message:
        (typeof error.response?.data?.detail === 'string' && error.response?.data?.detail) ||
        error.message ||
        'Request failed',
      status: error.response?.status,
    };
  }

  if (error instanceof Error) {
    return { message: error.message };
  }

  return { message: 'Unexpected error' };
}

export type SessionSummary = {
  session_id: string;
  topic: string;
  mode: string;
  premise: string;
  createdAt: string;
  workflowStage?: string;
  status?: string;
  latestScore?: number;
  latestFeedback?: string;
};

export function loadSessionSummaries(): SessionSummary[] {
  try {
    const raw = localStorage.getItem('juriscode.sessions');
    return raw ? (JSON.parse(raw) as SessionSummary[]) : [];
  } catch {
    return [];
  }
}

export function saveSessionSummary(session: SessionSummary) {
  const sessions = loadSessionSummaries();
  const next = [session, ...sessions.filter((entry) => entry.session_id !== session.session_id)].slice(0, 20);
  localStorage.setItem('juriscode.sessions', JSON.stringify(next));
  return next;
}
