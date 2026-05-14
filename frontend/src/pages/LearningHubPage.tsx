import { useMemo, useState } from 'react';
import { GlassCard } from '@/components/common/GlassCard';
import { Modal } from '@/components/common/Modal';
import { ProgressRing } from '@/components/common/ProgressRing';
import { TopicBadge } from '@/components/common/TopicBadge';
import { TranscriptBubble } from '@/components/common/TranscriptBubble';
import type { LearningFlashcard } from '@/types';
import { classNames } from '@/utils/classNames';

const modules = [
  { title: 'Courtroom objections', description: 'Hear objection types, response strategy, and evidentiary boundaries.', progress: 85, accent: 'electric' as const },
  { title: 'Burden of proof', description: 'Understand who must prove what, and how standard-of-proof changes the argument.', progress: 72, accent: 'emerald' as const },
  { title: 'Legal reasoning basics', description: 'Issue spotting, rule application, counter-argument handling, and conclusion framing.', progress: 66, accent: 'gold' as const },
  { title: 'Statutory interpretation', description: 'Use text, purpose, context, and precedent to read statutes carefully.', progress: 58, accent: 'electric' as const },
  { title: 'Mock trial techniques', description: 'Direct examination, cross-examination, pacing, and courtroom confidence.', progress: 90, accent: 'emerald' as const },
  { title: 'Legal glossary', description: 'Build vocabulary for claims, defenses, objections, and procedural concepts.', progress: 78, accent: 'gold' as const },
];

const flashcards: LearningFlashcard[] = [
  { front: 'What is an objection?', back: 'A formal challenge to evidence, questions, or procedure that the court must decide.', hint: 'Think: admissibility and fairness.' },
  { front: 'Why does burden of proof matter?', back: 'It determines which party must persuade the court on a disputed issue.', hint: 'Watch for standards like preponderance or beyond reasonable doubt.' },
  { front: 'What is statutory interpretation?', back: 'A method of determining the meaning and scope of legislative text.', hint: 'Text, context, and purpose all matter.' },
];

const quizOptions = [
  'State the rule, then connect facts.',
  'Focus only on emotional language.',
  'Skip counter-arguments to save time.',
];

const glossary = ['Ratio decidendi', 'Prima facie', 'Burden of proof', 'Objection sustained', 'Cross-examination', 'Material fact'];

export function LearningHubPage() {
  const [beginnerMode, setBeginnerMode] = useState(true);
  const [selectedCard, setSelectedCard] = useState(0);
  const [quizAnswer, setQuizAnswer] = useState('');
  const [selectedModule, setSelectedModule] = useState<string | null>(null);

  const currentCard = flashcards[selectedCard % flashcards.length];

  const learningTone = useMemo(() => (beginnerMode ? 'Beginner mode simplifies the concepts into clear practice goals.' : 'Advanced mode encourages deeper legal analysis and richer critique.'), [beginnerMode]);

  return (
    <div className="space-y-6 p-6">
      <GlassCard title="Learning hub" subtitle="Structured legal education for mock-trial practice">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="space-y-2">
            <TopicBadge label={beginnerMode ? 'Beginner mode' : 'Advanced mode'} active />
            <p className="text-sm leading-7 text-slate-700">{learningTone}</p>
          </div>
          <button
            type="button"
            onClick={() => setBeginnerMode((value) => !value)}
            className="rounded-full border border-amber-200/80 bg-white px-5 py-3 text-sm font-semibold text-slate-900 transition hover:border-electric/40 hover:bg-amber-100/70"
          >
            Toggle mode
          </button>
        </div>
      </GlassCard>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {modules.map((module) => (
          <button key={module.title} type="button" onClick={() => setSelectedModule(module.title)} className="text-left">
            <GlassCard className="h-full cursor-pointer transition hover:-translate-y-0.5 hover:border-electric/30">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-lg font-semibold text-slate-900">{module.title}</p>
                  <p className="mt-2 text-sm leading-7 text-slate-700">{module.description}</p>
                </div>
                <ProgressRing value={module.progress} label="Progress" size={128} />
              </div>
            </GlassCard>
          </button>
        ))}
      </section>

      <section className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
        <GlassCard title="Flashcards" subtitle="Tap through key courtroom concepts">
          <div className="space-y-4">
            <div className="min-h-[220px] rounded-3xl border border-amber-200/70 bg-white p-6 transition hover:border-electric/20">
              <p className="section-kicker">Card {selectedCard + 1} of {flashcards.length}</p>
              <div className="mt-4 space-y-4">
                <TranscriptBubble speaker="Front" tone="electric" content={currentCard.front} compact />
                <TranscriptBubble speaker="Back" tone="emerald" content={currentCard.back} compact />
                {currentCard.hint ? <p className="text-sm text-slate-600">Hint: {currentCard.hint}</p> : null}
              </div>
            </div>
            <div className="flex flex-wrap gap-3">
              <button type="button" onClick={() => setSelectedCard((value) => (value + 1) % flashcards.length)} className="rounded-full bg-electric px-5 py-2.5 text-sm font-semibold text-white transition hover:brightness-110">Next card</button>
              <button type="button" onClick={() => setSelectedCard(0)} className="rounded-full border border-amber-200/80 bg-white px-5 py-2.5 text-sm font-semibold text-slate-900 transition hover:border-electric/40">Reset</button>
            </div>
          </div>
        </GlassCard>

        <GlassCard title="Mini quiz" subtitle="Select the strongest learning behavior">
          <div className="space-y-4">
            {quizOptions.map((option) => (
              <label key={option} className={classNames('flex cursor-pointer items-start gap-3 rounded-2xl border p-4 transition', quizAnswer === option ? 'border-electric/30 bg-electric/10' : 'border-amber-200/70 bg-white hover:border-amber-300/70')}>
                <input type="radio" name="legal-quiz" value={option} checked={quizAnswer === option} onChange={(event) => setQuizAnswer(event.target.value)} className="mt-1 accent-electric" />
                <span className="text-sm leading-7 text-slate-700">{option}</span>
              </label>
            ))}
            <div className="rounded-2xl border border-amber-200/70 bg-white p-4 text-sm text-slate-700">
              <p className="font-semibold text-slate-900">Recommended answer</p>
              <p className="mt-2 leading-7">State the rule, then connect facts.</p>
            </div>
          </div>
        </GlassCard>
      </section>

      <GlassCard title="Legal glossary" subtitle="Vocabulary that supports better reasoning">
        <div className="flex flex-wrap gap-2">
          {glossary.map((term) => (
            <TopicBadge key={term} label={term} />
          ))}
        </div>
      </GlassCard>

      <Modal open={Boolean(selectedModule)} title={selectedModule ?? 'Module details'} onClose={() => setSelectedModule(null)}>
        <div className="space-y-4">
          <p className="text-sm leading-7 text-slate-700">
            {selectedModule === 'Courtroom objections'
              ? 'Learn why objections matter, how to name them, and how to respond without breaking the flow of argument.'
              : selectedModule === 'Burden of proof'
                ? 'Track who must prove a claim or defense and how the standard changes the strategy of the case.'
                : selectedModule === 'Statutory interpretation'
                  ? 'Study text, structure, and purpose so you can turn a statute into a usable legal argument.'
                  : selectedModule === 'Mock trial techniques'
                    ? 'Practice the choreography of a courtroom: pacing, questioning, and precision under pressure.'
                    : selectedModule === 'Legal glossary'
                      ? 'Build a vocabulary that helps you read, argue, and critique legal positions with confidence.'
                      : 'Open a module to review the learning objective.'}
          </p>
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="rounded-2xl border border-amber-200/70 bg-white p-4">
              <p className="text-xs uppercase tracking-[0.3em] text-slate-500">Why it matters</p>
              <p className="mt-2 text-sm leading-7 text-slate-700">These modules help students move from passive reading to active legal reasoning.</p>
            </div>
            <div className="rounded-2xl border border-amber-200/70 bg-white p-4">
              <p className="text-xs uppercase tracking-[0.3em] text-slate-500">Next practice step</p>
              <p className="mt-2 text-sm leading-7 text-slate-700">Use Practice Arena to test the concept in a courtroom simulation.</p>
            </div>
          </div>
        </div>
      </Modal>
    </div>
  );
}
