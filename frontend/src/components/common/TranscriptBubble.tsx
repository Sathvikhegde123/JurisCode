import { classNames } from '@/utils/classNames';

type TranscriptBubbleProps = {
  speaker: string;
  content: string;
  tone?: 'electric' | 'emerald' | 'gold' | 'slate';
  compact?: boolean;
};

export function TranscriptBubble({ speaker, content, tone = 'slate', compact = false }: TranscriptBubbleProps) {
  const styles =
    tone === 'emerald'
      ? 'border-emeraldGlow/30 bg-emeraldGlow/10 text-emeraldGlow'
      : tone === 'gold'
        ? 'border-mutedGold/30 bg-mutedGold/10 text-mutedGold'
        : tone === 'electric'
          ? 'border-electric/30 bg-electric/10 text-electric'
          : 'border-white/10 bg-white/5 text-slate-200';

  return (
    <div className={classNames('rounded-2xl border p-4', styles)}>
      <div className="flex items-center justify-between gap-3">
        <span className="text-xs uppercase tracking-[0.3em] opacity-80">{speaker}</span>
        <span className="h-2 w-2 rounded-full bg-current opacity-80" aria-hidden="true" />
      </div>
      <p className={classNames('mt-3 leading-7 text-white', compact ? 'text-sm' : 'text-[15px]')}>
        {content}
      </p>
    </div>
  );
}
