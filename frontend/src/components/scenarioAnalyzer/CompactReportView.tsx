import { GlassCard } from '@/components/common/GlassCard';
import { classNames } from '@/utils/classNames';

type CompactReportViewProps = {
  detectedIssue: string;
  situationOverview: string;
  keyPoints: string[];
  practicalNextSteps: string[];
  onContinueChat: () => void;
  onFullReport: () => void;
  onNewScenario: () => void;
};

export function CompactReportView({
  detectedIssue,
  situationOverview,
  keyPoints,
  practicalNextSteps,
  onContinueChat,
  onFullReport,
  onNewScenario,
}: CompactReportViewProps) {
  return (
    <div className="space-y-4">
      <GlassCard>
        <p className="text-xs uppercase tracking-[0.2em] text-slate-500">Detected issue</p>
        <h2 className="mt-1 text-xl font-semibold text-slate-900">{detectedIssue}</h2>
      </GlassCard>

      <GlassCard title="Situation overview" subtitle="Plain-language read of your scenario">
        <p className="text-sm leading-relaxed text-slate-800 sm:text-[15px]">{situationOverview}</p>
      </GlassCard>

      <GlassCard title="Key points to understand" subtitle="What usually matters next">
        <ul className="list-disc space-y-2 pl-5 text-sm leading-relaxed text-slate-800 sm:text-[15px]">
          {keyPoints.map((p) => (
            <li key={p}>{p}</li>
          ))}
        </ul>
      </GlassCard>

      <GlassCard title="Practical next steps" subtitle="Document and process checks, not legal advice">
        <ol className="list-decimal space-y-2 pl-5 text-sm leading-relaxed text-slate-800 sm:text-[15px]">
          {practicalNextSteps.map((s) => (
            <li key={s}>{s}</li>
          ))}
        </ol>
      </GlassCard>

      <div className="flex flex-wrap gap-3 pt-1">
        <button
          type="button"
          onClick={onContinueChat}
          className={classNames(
            'rounded-full bg-electric px-6 py-3 text-sm font-semibold text-white shadow-sm transition hover:brightness-110',
          )}
        >
          Continue chat
        </button>
        <button
          type="button"
          onClick={onFullReport}
          className="rounded-full border border-amber-200/80 bg-white px-6 py-3 text-sm font-semibold text-slate-900 transition hover:border-electric/40 hover:bg-amber-50/80"
        >
          View full report
        </button>
        <button
          type="button"
          onClick={onNewScenario}
          className="rounded-full border border-slate-200 bg-white px-6 py-3 text-sm font-semibold text-slate-700 transition hover:border-slate-300"
        >
          New scenario
        </button>
      </div>
    </div>
  );
}
