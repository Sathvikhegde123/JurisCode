import { Link } from 'react-router-dom';
import { Footer } from '@/components/layout/Footer';
import { Navbar } from '@/components/layout/Navbar';
import { GlassCard } from '@/components/common/GlassCard';
import { TranscriptBubble } from '@/components/common/TranscriptBubble';
import { TopicBadge } from '@/components/common/TopicBadge';

const features = [
  {
    title: 'Legal reasoning drills',
    description: 'Break down facts, issues, and authorities with structured courtroom-style practice.',
  },
  {
    title: 'Objection training',
    description: 'Practice evidentiary objections, burden analysis, and response framing in a safe learning loop.',
  },
  {
    title: 'Opposing counsel simulation',
    description: 'Test your argument against adversarial AI feedback that pushes for stronger reasoning.',
  },
  {
    title: 'Explainable AI workflow',
    description: 'See premise generation, challenge responses, and scoring in a transparent, educational flow.',
  },
];

const workflow = [
  'Choose a topic and mode.',
  'Generate a premise or start a mock trial.',
  'Write your argument and receive adversarial feedback.',
  'Review reasoning, score, and suggested improvements.',
];

export function LandingPage() {
  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,_rgba(249,115,22,0.18),_transparent_30%),radial-gradient(circle_at_top_right,_rgba(34,197,94,0.14),_transparent_28%),linear-gradient(180deg,_#fffaf3_0%,_#f7f1e3_100%)] text-slate-900">
      <Navbar />
      <main className="page-fade">
        <section className="mx-auto grid max-w-7xl gap-10 px-4 py-14 sm:px-6 lg:grid-cols-[1.2fr_0.8fr] lg:px-8 lg:py-20">
          <div className="space-y-7">
            <div className="flex flex-wrap items-center gap-3">
              <TopicBadge label="SDG 4: Quality Education" active />
              <TopicBadge label="Courtroom Simulation" />
              <TopicBadge label="Explainable AI" />
            </div>
            <div className="space-y-5">
              <p className="section-kicker">AI-powered legal education platform</p>
              <h1 className="max-w-3xl text-4xl font-semibold leading-tight text-slate-900 sm:text-5xl lg:text-6xl">
                Learn Legal Reasoning Through AI-Powered Mock Trials
              </h1>
              <p className="max-w-2xl text-lg leading-8 text-slate-700">
                Practice objections, challenge arguments, explore legal logic, and learn courtroom reasoning interactively.
              </p>
            </div>

            <div className="flex flex-wrap gap-4">
              <Link
                to="/practice"
                className="rounded-full bg-orange-600 px-6 py-3 font-semibold text-white shadow-sm transition hover:scale-[1.02] hover:brightness-110"
              >
                Start Practice
              </Link>
              <Link
                to="/learn"
                className="rounded-full border border-amber-200/80 bg-white px-6 py-3 font-semibold text-slate-900 transition hover:border-electric/40 hover:bg-amber-100/70"
              >
                Explore Learning Hub
              </Link>
            </div>

            <div className="grid gap-4 sm:grid-cols-2 stagger-children">
              {features.map((feature) => (
                <GlassCard key={feature.title} className="h-full">
                  <h2 className="text-lg font-semibold text-slate-900">{feature.title}</h2>
                  <p className="mt-3 text-sm leading-7 text-slate-700">{feature.description}</p>
                </GlassCard>
              ))}
            </div>
          </div>

          <div className="space-y-5">
            <GlassCard className="border-electric/20 bg-[#fff3e3]">
              <div className="flex items-center justify-between gap-4">
                <div>
                  <p className="section-kicker">Mock trial preview</p>
                  <h2 className="mt-2 text-xl font-semibold text-slate-900">Courtroom transcript</h2>
                </div>
                <span className="rounded-full border border-emeraldGlow/20 bg-emeraldGlow/10 px-3 py-1 text-xs text-emeraldGlow">
                  Live practice flow
                </span>
              </div>
              <div className="mt-5 space-y-3">
                <TranscriptBubble speaker="Judge" tone="gold" content="Counsel, present your strongest reasoning on the issue before the court." />
                <TranscriptBubble speaker="Student Advocate" tone="electric" content="I will frame the facts, isolate the governing rule, and test the opposing theory for weaknesses." />
                <TranscriptBubble speaker="AI Opposing Counsel" tone="emerald" content="I will challenge the missing facts, statutory interpretation, and any unsupported conclusion." />
              </div>
            </GlassCard>

            <GlassCard>
              <p className="section-kicker">Learning workflow</p>
              <div className="mt-4 space-y-3">
                {workflow.map((step, index) => (
                  <div key={step} className="flex items-start gap-3 rounded-2xl border border-amber-200/70 bg-white p-4">
                    <div className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-electric/15 text-sm font-semibold text-electric">
                      {index + 1}
                    </div>
                    <p className="text-sm leading-6 text-slate-700">{step}</p>
                  </div>
                ))}
              </div>
            </GlassCard>

            <GlassCard>
              <p className="section-kicker">SDG 4 alignment</p>
              <h2 className="mt-3 text-xl font-semibold text-slate-900">Accessible, explainable, practice-driven education</h2>
              <p className="mt-3 text-sm leading-7 text-slate-700">
                The platform supports structured legal reasoning, court literacy, and repeatable practice so students can build confidence without relying on legal advice.
              </p>
            </GlassCard>
          </div>
        </section>
      </main>
      <Footer />
    </div>
  );
}
