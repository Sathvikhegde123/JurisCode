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

export type PracticeSessionResponse = {
  id?: string;
  session_id?: string;
  topic?: string;
  mode?: string;
  workflow_stage?: string;
  session_status?: string;
  status?: string;
  current_round?: number;
  max_rounds?: number;
  metadata?: JsonRecord;
  [key: string]: unknown;
};

export type PracticePremiseResponse = {
  session_id?: string;
  premise?: JsonRecord | string;
  locked_facts?: string[];
  legal_issue_summary?: string;
  workflow_stage?: string;
  session_status?: string;
  current_round?: number;
  [key: string]: unknown;
};

export type PracticeWorkflowArgumentResponse = {
  id?: number;
  session_id?: string;
  round_number?: number;
  argument_type?: string;
  content?: string;
  hallucination_flags?: JsonRecord;
  workflow_stage?: string;
  session_status?: string;
  current_round?: number;
  [key: string]: unknown;
};

export type PracticeOpposingResponse = {
  id?: number;
  session_id?: string;
  content?: string;
  workflow_stage?: string;
  session_status?: string;
  current_round?: number;
  [key: string]: unknown;
};

export type PracticeJudgeEvaluationResponse = {
  session_id?: string;
  burden_of_proof_analysis?: string;
  contradictions_found?: string[];
  evidentiary_sufficiency?: string;
  advocacy_score?: number;
  procedural_discipline?: number;
  hallucination_penalty?: number;
  educational_feedback?: string;
  termination_recommendation?: string;
  learning_points?: string[];
  final_score?: number;
  workflow_stage?: string;
  session_status?: string;
  current_round?: number;
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
  premise?:
    | string
    | {
        title?: string;
        summary?: string;
        description?: string;
        text?: string;
        narrative?: string;
        scenario_text?: string;
      };
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
