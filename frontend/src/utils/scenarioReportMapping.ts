export type LawyerWarningShape = {
  required: boolean;
  reason: string;
};

export type CompactViewShape = {
  detected_issue: string;
  short_summary: string;
  main_points: string[];
  recommended_next_steps: string[];
  lawyer_warning: LawyerWarningShape;
  confidence: string;
  disclaimer: string;
};

function asStringList(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.map((item) => (typeof item === 'string' ? item : String(item))).filter(Boolean);
}

function pickString(value: unknown, fallback = '') {
  return typeof value === 'string' && value.trim() ? value : fallback;
}

function polishPackId(s: string) {
  return s
    .replace(/_/g, ' ')
    .split(' ')
    .filter(Boolean)
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase())
    .join(' ');
}

export function deriveCompactFromFullReport(fullReport: Record<string, unknown>): CompactViewShape {
  const rawIssue = pickString(fullReport.issue_type) || pickString(fullReport.detected_domain) || 'Legal issue';
  const issue = polishPackId(rawIssue);
  const summary =
    pickString(fullReport.scenario_summary) || pickString(fullReport.simplified_explanation) || '';
  const facts = asStringList(fullReport.facts_identified);
  const missing = asStringList(fullReport.missing_facts);
  const remedies = asStringList(fullReport.possible_remedies);
  const rights = asStringList(fullReport.rights_possibly_involved);
  const mainPoints = [...facts, ...missing.slice(0, 4)].slice(0, 14);
  const steps = remedies.length > 0 ? remedies : rights;
  const consult = fullReport.consult_lawyer_warning === true;
  const reason =
    pickString(fullReport.warning_reason) ||
    (consult ? 'A lawyer can help with documents, forums, and strategy for your situation.' : '');

  return {
    detected_issue: issue,
    short_summary: summary,
    main_points:
      mainPoints.length > 0
        ? mainPoints
        : [pickString(fullReport.simplified_explanation) || 'Open the full report for structured detail.'].filter(
            Boolean,
          ),
    recommended_next_steps: steps.slice(0, 10),
    lawyer_warning: { required: consult, reason },
    confidence: pickString(fullReport.confidence) || '—',
    disclaimer:
      pickString(fullReport.disclaimer) ||
      'This is legal information for awareness and education, not legal advice.',
  };
}
