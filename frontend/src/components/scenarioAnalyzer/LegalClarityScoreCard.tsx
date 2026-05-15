import { useState } from 'react';
import { classNames } from '@/utils/classNames';
import type { LegalClarityScoreResponse } from '@/api/scenarioAnalyzerApi';

type CategoryKey = keyof LegalClarityScoreResponse['score_breakdown'];

const CATEGORY_ORDER: { key: CategoryKey; title: string; max: number }[] = [
  { key: 'issue_understanding', title: 'Issue Understanding', max: 25 },
  { key: 'fact_clarity', title: 'Fact Clarity', max: 30 },
  { key: 'document_clarity', title: 'Document Clarity', max: 25 },
  { key: 'risk_clarity', title: 'Risk Clarity', max: 20 },
];

const SUB_LABELS: Record<CategoryKey, { key: string; label: string }[]> = {
  issue_understanding: [
    { key: 'issue_category_detected', label: 'Issue category detected' },
    { key: 'specific_sub_issue_detected', label: 'Specific sub-issue detected' },
    { key: 'user_confirmed_or_refined_issue', label: 'User confirmed/refined issue' },
  ],
  fact_clarity: [
    { key: 'ownership_or_history_clarified', label: 'Ownership/history clarified' },
    { key: 'timeline_clarified', label: 'Timeline clarified' },
    { key: 'possession_clarified', label: 'Possession clarified' },
    { key: 'parties_or_legal_heirs_clarified', label: 'Parties/legal heirs clarified' },
    { key: 'current_dispute_trigger_clarified', label: 'Current dispute trigger clarified' },
  ],
  document_clarity: [
    { key: 'core_document_mentioned', label: 'Core document mentioned' },
    { key: 'mutation_or_revenue_record_mentioned', label: 'Mutation/revenue record mentioned' },
    { key: 'receipt_or_payment_proof_mentioned', label: 'Receipt/payment proof mentioned' },
    { key: 'notice_complaint_or_court_papers_mentioned', label: 'Notice/complaint/court papers mentioned' },
    { key: 'missing_documents_identified', label: 'Missing documents identified' },
  ],
  risk_clarity: [
    { key: 'urgency_detected', label: 'Urgency detected' },
    { key: 'possession_or_dispossession_risk_clarified', label: 'Possession/dispossession risk clarified' },
    { key: 'fraud_forgery_or_mutation_change_clarified', label: 'Fraud/forgery/mutation change clarified' },
    { key: 'lawyer_police_or_court_trigger_clarified', label: 'Lawyer/police/court trigger clarified' },
  ],
};

function badgeClass(level: string) {
  const l = level.toLowerCase();
  if (l.includes('strong')) {
    return 'border-emerald-200 bg-emerald-50 text-emerald-900';
  }
  if (l.includes('good')) {
    return 'border-sky-200 bg-sky-50 text-sky-900';
  }
  if (l.includes('basic')) {
    return 'border-amber-200 bg-amber-50 text-amber-950';
  }
  return 'border-slate-200 bg-slate-50 text-slate-800';
}

export function LegalClarityScoreCard({ score }: { score: LegalClarityScoreResponse }) {
  const [open, setOpen] = useState<CategoryKey | null>(null);
  const pct = Math.max(0, Math.min(100, score.legal_clarity_score));

  return (
    <div className="rounded-3xl border border-amber-200/70 bg-white/95 p-5 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-3 border-b border-amber-200/60 pb-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-600">Legal Clarity Score</p>
          <p className="mt-1 text-3xl font-bold text-slate-900">
            {score.legal_clarity_score}
            <span className="text-lg font-semibold text-slate-500">/100</span>
          </p>
        </div>
        <span
          className={classNames(
            'inline-flex items-center rounded-full border px-3 py-1 text-xs font-semibold',
            badgeClass(score.clarity_level),
          )}
        >
          {score.clarity_level}
        </span>
      </div>

      <p className="mt-3 text-sm text-slate-700">
        This score measures how clearly your scenario was clarified. It does not predict legal outcome.
      </p>

      <div className="mt-4">
        <div className="h-2.5 w-full overflow-hidden rounded-full bg-amber-100">
          <div
            className="h-full rounded-full bg-electric transition-[width] duration-500"
            style={{ width: `${pct}%` }}
          />
        </div>
      </div>

      <div className="mt-6 space-y-3">
        {CATEGORY_ORDER.map(({ key, title, max }) => {
          const block = score.score_breakdown[key];
          const expanded = open === key;
          return (
            <div key={key} className="rounded-2xl border border-amber-200/60 bg-[#fffaf3]/80">
              <button
                type="button"
                className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left"
                onClick={() => setOpen(expanded ? null : key)}
              >
                <div>
                  <p className="text-sm font-semibold text-slate-900">{title}</p>
                  <p className="text-xs text-slate-600">
                    {block.score}/{max}
                  </p>
                </div>
                <span className="text-xs font-semibold text-slate-500">{expanded ? '−' : '+'}</span>
              </button>
              <div className="border-t border-amber-200/50 px-4 py-3 text-sm text-slate-700">
                <p className="leading-relaxed">{block.reason}</p>
                {expanded ? (
                  <ul className="mt-3 space-y-2 text-xs text-slate-700">
                    {SUB_LABELS[key].map((row) => (
                      <li key={row.key} className="flex justify-between gap-3 border-b border-amber-200/40 pb-2 last:border-0">
                        <span>{row.label}</span>
                        <span className="shrink-0 font-semibold text-slate-900">
                          {Number(block.sub_scores[row.key as keyof typeof block.sub_scores] ?? 0)}
                        </span>
                      </li>
                    ))}
                  </ul>
                ) : null}
              </div>
            </div>
          );
        })}
      </div>

      {score.strengths.length > 0 ? (
        <div className="mt-6">
          <p className="text-sm font-semibold text-slate-900">Strengths</p>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-700">
            {score.strengths.map((s) => (
              <li key={s}>{s}</li>
            ))}
          </ul>
        </div>
      ) : null}

      {score.remaining_gaps.length > 0 ? (
        <div className="mt-4">
          <p className="text-sm font-semibold text-slate-900">Remaining gaps</p>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-700">
            {score.remaining_gaps.map((s) => (
              <li key={s}>{s}</li>
            ))}
          </ul>
        </div>
      ) : null}

      {score.summary_feedback ? (
        <div className="mt-4 rounded-2xl border border-amber-200/60 bg-white/90 px-4 py-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-600">Summary feedback</p>
          <p className="mt-2 text-sm leading-relaxed text-slate-800">{score.summary_feedback}</p>
        </div>
      ) : null}

      <p className="mt-4 text-xs leading-relaxed text-slate-600">{score.teacher_explanation}</p>

      <p className="mt-4 text-[11px] text-slate-500">
        This is a clarity and learning metric, not legal advice.
      </p>
    </div>
  );
}
