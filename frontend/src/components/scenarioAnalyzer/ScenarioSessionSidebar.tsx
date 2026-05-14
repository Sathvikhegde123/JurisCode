import { TopicBadge } from '@/components/common/TopicBadge';
import type { ScenarioSessionListItem } from '@/api/scenarioAnalyzerApi';
import { MessageCircleIcon } from '@/components/scenarioAnalyzer/ScenarioIcons';
import { classNames } from '@/utils/classNames';

type ScenarioSessionSidebarProps = {
  sessions: ScenarioSessionListItem[];
  selectedSessionId: string | null;
  sessionsError: string;
  mobileOpen: boolean;
  onMobileOpenChange: (open: boolean) => void;
  onSelectSession: (session: ScenarioSessionListItem) => void;
  onNewScenario: () => void;
};

function preview(text: string, max = 120) {
  const t = text.replace(/\s+/g, ' ').trim();
  if (t.length <= max) {
    return t;
  }
  return `${t.slice(0, max)}…`;
}

export function ScenarioSessionSidebar({
  sessions,
  selectedSessionId,
  sessionsError,
  mobileOpen,
  onMobileOpenChange,
  onSelectSession,
  onNewScenario,
}: ScenarioSessionSidebarProps) {
  return (
    <>
      <div className="mb-3 flex items-center justify-between xl:hidden">
        <button
          type="button"
          onClick={() => onMobileOpenChange(!mobileOpen)}
          className="inline-flex items-center gap-2 rounded-2xl border border-amber-200/80 bg-white px-4 py-2 text-sm font-semibold text-slate-900"
        >
          <MessageCircleIcon />
          {mobileOpen ? 'Hide sessions' : 'Recent sessions'}
        </button>
      </div>

      <aside
        className={classNames(
          'shrink-0 rounded-3xl border border-amber-200/70 bg-white/90 shadow-sm xl:w-[280px]',
          mobileOpen ? 'block' : 'hidden',
          'xl:block',
        )}
      >
        <div className="border-b border-amber-200/60 px-4 py-3">
          <p className="text-sm font-semibold text-slate-900">Recent Legal Scenarios</p>
          {sessionsError ? <p className="mt-1 text-xs text-amber-900">{sessionsError}</p> : null}
        </div>

        <div className="p-3">
          <button
            type="button"
            onClick={() => {
              onNewScenario();
              onMobileOpenChange(false);
            }}
            className="mb-3 flex w-full items-center justify-center gap-2 rounded-2xl border border-dashed border-electric/40 bg-electric/5 py-2.5 text-sm font-semibold text-electric transition hover:bg-electric/10"
          >
            + New scenario
          </button>

          <div className="max-h-[min(420px,50vh)] space-y-2 overflow-y-auto pr-1 xl:max-h-[calc(100vh-280px)]">
            {sessions.length === 0 ? (
              <p className="px-1 text-xs text-slate-600">No saved sessions yet. Analyze a scenario to see it here.</p>
            ) : (
              sessions.map((s) => (
                <button
                  key={s.session_id}
                  type="button"
                  onClick={() => {
                    onSelectSession(s);
                    onMobileOpenChange(false);
                  }}
                  className={classNames(
                    'w-full rounded-2xl border px-3 py-2.5 text-left text-sm transition',
                    selectedSessionId === s.session_id
                      ? 'border-electric/40 bg-electric/10 shadow-sm'
                      : 'border-amber-200/60 bg-white hover:border-amber-300/80',
                  )}
                >
                  <p className="line-clamp-2 text-slate-900">{preview(s.original_scenario)}</p>
                  <div className="mt-2 flex flex-wrap items-center gap-2">
                    <TopicBadge label={s.issue_type || 'General'} />
                    <span className="text-[10px] uppercase tracking-wide text-slate-500">
                      {s.created_at ? new Date(s.created_at).toLocaleString() : ''}
                    </span>
                  </div>
                </button>
              ))
            )}
          </div>
        </div>
      </aside>
    </>
  );
}
