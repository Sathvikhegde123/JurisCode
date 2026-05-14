import { useMemo, useState } from 'react';
import { EmptyState } from '@/components/common/EmptyState';
import { GlassCard } from '@/components/common/GlassCard';
import { SearchBar } from '@/components/common/SearchBar';
import { SessionCard } from '@/components/common/SessionCard';
import { TopicBadge } from '@/components/common/TopicBadge';
import { loadSessionSummaries } from '@/services/api';

export function SessionsPage() {
  const [query, setQuery] = useState('');
  const [activeFilter, setActiveFilter] = useState<'all' | 'scored' | 'recent'>('all');
  const sessions = loadSessionSummaries();

  const filtered = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    return sessions.filter((session) => {
      const matchesQuery = !normalized || [session.topic, session.mode, session.premise, session.latestFeedback ?? ''].join(' ').toLowerCase().includes(normalized);
      const matchesFilter =
        activeFilter === 'all' ||
        (activeFilter === 'scored' && typeof session.latestScore === 'number') ||
        (activeFilter === 'recent' && Boolean(session.latestFeedback));
      return matchesQuery && matchesFilter;
    });
  }, [activeFilter, query, sessions]);

  return (
    <div className="space-y-6">
      <GlassCard title="Session history" subtitle="Search your prior mock trials and review the score timeline">
        <div className="grid gap-4 lg:grid-cols-[1fr_auto]">
          <SearchBar value={query} onChange={setQuery} placeholder="Search by topic, mode, or feedback" />
          <div className="flex flex-wrap gap-2">
            {(['all', 'scored', 'recent'] as const).map((filter) => (
              <button key={filter} type="button" onClick={() => setActiveFilter(filter)}>
                <TopicBadge label={filter === 'all' ? 'All' : filter === 'scored' ? 'With scores' : 'Recent feedback'} active={activeFilter === filter} />
              </button>
            ))}
          </div>
        </div>
      </GlassCard>

      {filtered.length ? (
        <div className="space-y-4">
          {filtered.map((session) => (
            <SessionCard key={session.session_id} session={session} />
          ))}
        </div>
      ) : (
        <EmptyState
          title="No matching sessions"
          description="Try a different search term or start a practice round to populate your courtroom history."
        />
      )}
    </div>
  );
}
