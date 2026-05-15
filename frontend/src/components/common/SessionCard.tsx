import { useEffect, useState } from 'react';
import { GlassCard } from './GlassCard';
import { formatShortDate, formatPercent } from '@/utils/format';
import type { SessionSummary } from '@/services/api';
import { getPracticeSession } from '@/services/legalApi';
import { TopicBadge } from './TopicBadge';
import { ScoreMeter } from './ScoreMeter';

type SessionCardSession = Omit<SessionSummary, 'premise'> & {
  premise: string | {
    title?: string;
    summary?: string;
    description?: string;
    text?: string;
    narrative?: string;
  };
};

function getPremiseHeading(premise: SessionCardSession['premise']) {
  if (typeof premise === 'string') {
    return premise;
  }

  return premise.title ?? premise.summary ?? premise.description ?? premise.text ?? premise.narrative ?? 'Premise generated.';
}

type SessionCardProps = {
  session: SessionCardSession;
};

export function SessionCard({ session }: SessionCardProps) {
  const [premiseTitle, setPremiseTitle] = useState(() => getPremiseHeading(session.premise));

  useEffect(() => {
    let isActive = true;

    async function loadSessionTitle() {
      try {
        const detail = await getPracticeSession(session.session_id);
        const premise = detail.premise as
          | string
          | {
              title?: string;
              summary?: string;
              description?: string;
              text?: string;
              narrative?: string;
              scenario_text?: string;
            }
          | undefined;

        const title = getPremiseHeading(
          premise ?? session.premise,
        );

        if (isActive) {
          setPremiseTitle(title);
        }
      } catch {
        if (isActive) {
          setPremiseTitle(getPremiseHeading(session.premise));
        }
      }
    }

    void loadSessionTitle();

    return () => {
      isActive = false;
    };
  }, [session.premise, session.session_id]);

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
              <h3 className="mt-3 text-lg font-semibold text-slate-900">{premiseTitle}</h3>
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
