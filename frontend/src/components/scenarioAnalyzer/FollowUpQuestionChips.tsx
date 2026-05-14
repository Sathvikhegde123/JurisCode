type FollowUpQuestionChipsProps = {
  questions: string[];
  onSelect: (q: string) => void;
  disabled?: boolean;
};

export function FollowUpQuestionChips({ questions, onSelect, disabled }: FollowUpQuestionChipsProps) {
  if (!questions.length) {
    return null;
  }

  return (
    <div className="flex flex-wrap gap-2">
      {questions.map((q) => (
        <button
          key={q}
          type="button"
          disabled={disabled}
          onClick={() => onSelect(q)}
          className="max-w-full rounded-full border border-amber-200/80 bg-white px-3 py-1.5 text-left text-xs font-medium text-slate-800 transition hover:border-electric/40 hover:bg-amber-50/80 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {q}
        </button>
      ))}
    </div>
  );
}
