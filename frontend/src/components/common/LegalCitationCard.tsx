import { GlassCard } from './GlassCard';

type LegalCitationCardProps = {
  title: string;
  citations: string[];
  tone?: 'electric' | 'emerald' | 'gold';
};

export function LegalCitationCard({ title, citations, tone = 'electric' }: LegalCitationCardProps) {
  const accent =
    tone === 'emerald' ? 'border-emeraldGlow/30 text-emeraldGlow' : tone === 'gold' ? 'border-mutedGold/30 text-mutedGold' : 'border-electric/30 text-electric';

  return (
    <GlassCard>
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className={`text-xs uppercase tracking-[0.35em] ${accent}`}>{title}</p>
          <div className="mt-3 flex flex-wrap gap-2">
            {citations.length ? citations.map((citation) => (
              <span key={citation} className="rounded-full border border-amber-200/70 bg-white px-3 py-1 text-sm text-slate-800">
                {citation}
              </span>
            )) : <span className="text-sm text-slate-600">No citations returned. Use the response to anchor statutory references.</span>}
          </div>
        </div>
      </div>
    </GlassCard>
  );
}
