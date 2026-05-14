type SearchBarProps = {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
};

export function SearchBar({ value, onChange, placeholder = 'Search sessions' }: SearchBarProps) {
  return (
    <label className="flex items-center gap-3 rounded-2xl border border-amber-200/70 bg-white px-4 py-3 text-slate-700 transition focus-within:border-electric/40 focus-within:ring-2 focus-within:ring-electric/20">
      <span className="text-sm">Search</span>
      <input
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        className="w-full bg-transparent text-sm text-slate-900 placeholder:text-slate-500 focus:outline-none"
      />
    </label>
  );
}
