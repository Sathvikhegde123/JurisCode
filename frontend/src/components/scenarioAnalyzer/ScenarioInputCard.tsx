import { GlassCard } from '@/components/common/GlassCard';

const EXAMPLES = [
  'My landlord is forcing me to leave before the agreement ends.',
  'My uncle sold ancestral property without informing us.',
  'Builder delayed my flat possession for two years.',
  'My brother changed mutation records after my father died.',
  'I bought land through a registered sale deed but the seller’s brother is disputing it.',
  'The builder is not giving possession even after taking most of the payment.',
  'My tenant is refusing to vacate after the lease ended.',
  'My name was removed from property records without notice.',
];

type ScenarioInputCardProps = {
  scenario: string;
  onScenarioChange: (v: string) => void;
  onAnalyze: () => void;
  loading: boolean;
  backendOnline: boolean | null;
};

export function ScenarioInputCard({
  scenario,
  onScenarioChange,
  onAnalyze,
  loading,
  backendOnline,
}: ScenarioInputCardProps) {
  const tooShort = scenario.trim().length > 0 && scenario.trim().length < 10;
  const canSubmit = scenario.trim().length >= 10 && !loading;

  return (
    <GlassCard
      title="Citizen Legal Scenario Analyzer"
      subtitle="Describe your legal issue in simple words. This tool gives legal awareness, possible next steps, and follow-up questions. It is not legal advice."
    >
      {backendOnline === false ? (
        <div className="mb-4 rounded-2xl border border-red-200/80 bg-red-50/90 px-4 py-3 text-sm text-red-950">
          Scenario Analyzer backend is not reachable. Please make sure it is running on port 8001.
        </div>
      ) : null}

      <div className="mb-5 flex flex-wrap gap-2">
        <span className="w-full text-xs font-medium uppercase tracking-wide text-slate-500">Examples</span>
        {EXAMPLES.map((ex) => (
          <button
            key={ex}
            type="button"
            onClick={() => onScenarioChange(ex)}
            className="rounded-full border border-amber-200/80 bg-amber-50/60 px-3 py-1.5 text-left text-xs leading-snug text-slate-800 transition hover:border-electric/40 sm:text-[13px]"
          >
            {ex}
          </button>
        ))}
      </div>

      <form
        className="space-y-5"
        onSubmit={(e) => {
          e.preventDefault();
          if (canSubmit) {
            onAnalyze();
          }
        }}
      >
        <label className="block space-y-2">
          <span className="text-sm font-medium text-slate-800">Your scenario</span>
          <textarea
            value={scenario}
            onChange={(e) => onScenarioChange(e.target.value)}
            rows={9}
            placeholder="Describe your legal issue here..."
            className="w-full min-h-[220px] resize-y rounded-2xl border border-amber-200/80 bg-white px-4 py-3 text-sm leading-relaxed text-slate-900 shadow-inner outline-none transition focus:border-electric/50 focus:ring-2 focus:ring-electric/20 sm:text-[15px]"
          />
        </label>

        {tooShort ? (
          <p className="text-sm text-amber-800">Please describe your issue in at least 10 characters.</p>
        ) : null}

        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <button
            type="submit"
            disabled={!canSubmit}
            title="You can also press Enter to submit when your scenario is ready."
            className="w-full rounded-full bg-electric px-8 py-3.5 text-base font-semibold text-white shadow-sm transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-50 sm:w-auto sm:min-w-[200px]"
          >
            Analyze scenario
          </button>
        </div>
      </form>
    </GlassCard>
  );
}
