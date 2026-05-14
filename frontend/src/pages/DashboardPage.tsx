import { Link } from 'react-router-dom';
import { DashboardStatCard } from '@/components/common/DashboardStatCard';
import { EmptyState } from '@/components/common/EmptyState';
import { GlassCard } from '@/components/common/GlassCard';
import { LoadingSpinner } from '@/components/common/LoadingSpinner';
import { ProgressRing } from '@/components/common/ProgressRing';
import { ScoreMeter } from '@/components/common/ScoreMeter';
import { SessionCard } from '@/components/common/SessionCard';
import { TopicBadge } from '@/components/common/TopicBadge';
import { loadSessionSummaries } from '@/services/api';
import { formatNumber, formatPercent } from '@/utils/format';
import { useEffect, useState } from 'react';

const recommendedTopics = ['Burden of proof', 'Objections', 'Statutory interpretation', 'Cross-examination'];

export function DashboardPage() {
  const [sessions, setSessions] = useState(loadSessionSummaries());
  const [ready, setReady] = useState(false);

  useEffect(() => {
    setSessions(loadSessionSummaries());
    setReady(true);
  }, []);

  const completed = sessions.length;
  const averageScore = completed
    ? Math.round(sessions.reduce((sum, session) => sum + (session.latestScore ?? 0), 0) / completed)
    : 0;
  const streak = Math.max(2, Math.min(18, completed + 2));
  const xp = 1200 + completed * 180;

  if (!ready) {
    return (
      <div className="space-y-6">
        <LoadingSpinner label="Loading dashboard" />
        <div className="grid gap-4 lg:grid-cols-2 xl:grid-cols-4">
          {Array.from({ length: 4 }).map((_, index) => (
            <div key={index} className="h-28 rounded-3xl border border-white/10 bg-white/5" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <section className="grid gap-4 xl:grid-cols-[1.6fr_0.8fr]">
        <GlassCard className="bg-gradient-to-br from-[#0d1f38] to-[#09111d]">
          <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
            <div className="max-w-2xl">
              <p className="section-kicker">Welcome back</p>
              <h1 className="mt-3 text-3xl font-semibold text-white sm:text-4xl">Build courtroom fluency through legal practice loops.</h1>
              <p className="mt-4 text-sm leading-7 text-slate-300">
                Continue structured mock trial practice, analyze opposing arguments, and strengthen legal reasoning with transparent AI feedback.
              </p>
              <div className="mt-6 flex flex-wrap gap-3">
                <TopicBadge label={`Streak ${streak} days`} active />
                <TopicBadge label={`${formatNumber(xp)} XP`} />
                <TopicBadge label={`${completed} completed sessions`} />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3 sm:max-w-sm">
              <DashboardStatCard title="Average score" value={formatPercent(averageScore)} caption="Across your recent sessions" tone="emerald" />
              <DashboardStatCard title="Progress" value={`${completed}`} caption="Practice rounds finished" tone="gold" />
            </div>
          </div>
        </GlassCard>

        <GlassCard className="flex items-center justify-center">
          <ProgressRing value={averageScore || 64} label="Momentum" />
        </GlassCard>
      </section>

      <section className="grid gap-4 lg:grid-cols-2 xl:grid-cols-4">
        <DashboardStatCard title="Practice Mock Trial" value="Start" caption="Generate a new premise and write your argument" />
        <DashboardStatCard title="Challenge My Argument" value="Adversarial" caption="Pressure-test any premise or draft argument" tone="emerald" />
        <DashboardStatCard title="Learning Modules" value="8" caption="Courtroom objections, burden of proof, and more" tone="gold" />
        <DashboardStatCard title="Session History" value={String(completed)} caption="Review performance trends and feedback" />
      </section>

      <section className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
        <div className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <GlassCard title="Practice quality" subtitle="A simple progress view of your recent work">
              <ScoreMeter score={averageScore || 67} label="Argument score" />
              <div className="mt-5 space-y-3">
                <div>
                  <div className="mb-2 flex justify-between text-sm text-slate-300"><span>Reasoning structure</span><span>82%</span></div>
                  <div className="h-2 rounded-full bg-white/10"><div className="h-2 w-[82%] rounded-full bg-electric" /></div>
                </div>
                <div>
                  <div className="mb-2 flex justify-between text-sm text-slate-300"><span>Statutory support</span><span>71%</span></div>
                  <div className="h-2 rounded-full bg-white/10"><div className="h-2 w-[71%] rounded-full bg-emeraldGlow" /></div>
                </div>
                <div>
                  <div className="mb-2 flex justify-between text-sm text-slate-300"><span>Counter-argument handling</span><span>64%</span></div>
                  <div className="h-2 rounded-full bg-white/10"><div className="h-2 w-[64%] rounded-full bg-mutedGold" /></div>
                </div>
              </div>
            </GlassCard>

            <GlassCard title="Recommended topics" subtitle="Suggested next practice areas">
              <div className="flex flex-wrap gap-2">
                {recommendedTopics.map((topic) => (
                  <TopicBadge key={topic} label={topic} />
                ))}
              </div>
              <div className="mt-6 rounded-2xl border border-white/10 bg-white/5 p-4">
                <p className="text-xs uppercase tracking-[0.3em] text-slate-500">AI feedback summary</p>
                <p className="mt-3 text-sm leading-7 text-slate-300">
                  Your arguments are strongest when you identify the rule, state the missing fact, and directly answer the most likely objection.
                </p>
              </div>
            </GlassCard>
          </div>

          <GlassCard title="Recent sessions" subtitle="Your latest mock trial practice history">
            {sessions.length ? (
              <div className="space-y-4">
                {sessions.slice(0, 3).map((session) => (
                  <SessionCard key={session.session_id} session={session} />
                ))}
              </div>
            ) : (
              <EmptyState
                title="No sessions yet"
                description="Start a practice round to see your session history, scores, and feedback here."
                action={<Link to="/practice" className="rounded-full bg-electric px-5 py-2.5 font-semibold text-white transition hover:brightness-110">Start Practice</Link>}
              />
            )}
          </GlassCard>
        </div>

        <div className="space-y-4">
          <GlassCard title="Session insights" subtitle="What the AI is noticing across your work">
            <div className="space-y-4">
              <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                <p className="text-sm font-semibold text-white">Strongest skill</p>
                <p className="mt-2 text-sm text-slate-300">Issue spotting and moving from fact to rule.</p>
              </div>
              <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                <p className="text-sm font-semibold text-white">Needs focus</p>
                <p className="mt-2 text-sm text-slate-300">Citing supporting authority and anticipating rebuttal.</p>
              </div>
              <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                <p className="text-sm font-semibold text-white">Next milestone</p>
                <p className="mt-2 text-sm text-slate-300">Reach 80% average on three consecutive mock trial turns.</p>
              </div>
            </div>
          </GlassCard>
        </div>
      </section>
    </div>
  );
}
