import { GlassCard } from './GlassCard';
import { formatShortDate, formatPercent } from '@/utils/format';
import type { SessionSummary } from '@/services/api';
import { TopicBadge } from './TopicBadge';
import { ScoreMeter } from './ScoreMeter';

type SessionCardProps = {
  session: SessionSummary;
};

export function SessionCard({ session }: SessionCardProps) {
  return (
    <GlassCard className="overflow-hidden">
      <details className="group">
        <summary className="cursor-pointer list-none outline-none">
          <div className="flex items-start justify-between gap-4">
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <TopicBadge label={session.topic} active />
                <span className="text-xs uppercase tracking-[0.25em] text-slate-500">{session.mode}</span>
              </div>
              <h3 className="mt-3 text-lg font-semibold text-slate-900">{session.premise.scenario_text}</h3>
              <p className="mt-2 text-sm text-slate-600">{formatShortDate(session.createdAt)}</p>
            </div>
            <span className="rounded-full border border-amber-200/70 bg-white px-3 py-1 text-sm text-slate-900">{session.latestScore ? formatPercent(session.latestScore) : 'New'}</span>
          </div>
        </summary>
        <div className="mt-5 grid gap-4 border-t border-amber-200/70 pt-4 sm:grid-cols-[1.4fr_1fr]">
          <div>
            <p className="text-xs uppercase tracking-[0.3em] text-slate-500">Latest feedback</p>
            <p className="mt-2 text-sm leading-6 text-slate-700">{session.latestFeedback ?? 'No feedback captured yet.'}</p>
          </div>
          <div>
            <ScoreMeter score={session.latestScore ?? 0} label="Session score" />
          </div>
        </div>
      </details>
    </GlassCard>
  );
}
