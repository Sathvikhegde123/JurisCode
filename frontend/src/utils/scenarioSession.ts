const SCENARIO_SESSION_KEY = 'juriscode_scenario_session_id';

export function getScenarioSessionId(): string | null {
  return localStorage.getItem(SCENARIO_SESSION_KEY);
}

export function setScenarioSessionId(sessionId: string) {
  if (sessionId) {
    localStorage.setItem(SCENARIO_SESSION_KEY, sessionId);
  }
}

export function clearScenarioSessionId() {
  localStorage.removeItem(SCENARIO_SESSION_KEY);
}
