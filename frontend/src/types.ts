export type JsonRecord = Record<string, unknown>;

export type HealthResponse = {
  status?: string;
  device?: string;
  models_loaded?: boolean;
  [key: string]: unknown;
};

export type ModelsStatusResponse = {
  device?: string;
  dtype?: string;
  backend_status?: string;
  active_adapter?: string;
  adapters_loaded?: boolean;
  models_loaded?: boolean;
  [key: string]: unknown;
};

export type TopicListResponse = {
  topics?: string[];
};

export type ModeListResponse = {
  modes?: string[];
};

export type PracticeStartResponse = {
  session_id?: string;
  premise?: string;
  topic?: string;
  mode?: string;
  metadata?: JsonRecord;
  [key: string]: unknown;
};

export type PracticeArgumentResponse = {
  opposing_response?: string;
  objection_feedback?: JsonRecord;
  score?: number;
  metadata?: JsonRecord;
  [key: string]: unknown;
};

export type ChallengeResponse = {
  opposing_response?: string;
  statutory_citations?: string[];
  socratic_questions?: string[];
  metadata?: JsonRecord;
  [key: string]: unknown;
};

export type SessionDetailsResponse = {
  session_id?: string;
  topic?: string;
  mode?: string;
  premise?: string;
  history?: Array<JsonRecord>;
  [key: string]: unknown;
};

export type DashboardModule = {
  title: string;
  description: string;
  progress: number;
  accent: 'electric' | 'emerald' | 'gold';
};

export type LearningFlashcard = {
  front: string;
  back: string;
  hint?: string;
};
