import type { LawyerWarningShape } from '@/utils/scenarioReportMapping';

type LawyerWarningCardProps = {
  warning: LawyerWarningShape;
  subtle?: boolean;
};

export function LawyerWarningCard({ warning, subtle }: LawyerWarningCardProps) {
  if (!warning.required && subtle) {
    return (
      <div className="rounded-2xl border border-amber-200/60 bg-amber-50/40 px-4 py-3 text-sm text-slate-700">
        <p className="font-medium text-slate-800">When to involve a lawyer</p>
        <p className="mt-1 leading-relaxed">If deadlines, court filings, or large sums are involved, consider professional advice.</p>
      </div>
    );
  }

  if (!warning.required) {
    return (
      <div className="rounded-2xl border border-slate-200/80 bg-slate-50/80 px-4 py-3 text-sm text-slate-600">
        General awareness only — not a substitute for a lawyer if your matter is contested or urgent.
      </div>
    );
  }

  return (
    <div className="rounded-2xl border border-red-200/80 bg-red-50/90 px-4 py-3 shadow-sm">
      <p className="text-sm font-semibold text-red-900">Lawyer consultation suggested</p>
      <p className="mt-2 text-sm leading-relaxed text-red-950/90">{warning.reason || 'This situation may need tailored legal advice.'}</p>
    </div>
  );
}
