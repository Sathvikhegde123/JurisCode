import { Link, NavLink } from 'react-router-dom';
import { MessageCircleIcon } from '@/components/scenarioAnalyzer/ScenarioIcons';
import { classNames } from '@/utils/classNames';

const navItems = [
  { to: '/dashboard', label: 'Dashboard' },
  { to: '/practice', label: 'Practice' },
  { to: '/challenge', label: 'Challenge' },
  { to: '/sessions', label: 'Sessions' },
  { to: '/models', label: 'Models' },
  { to: '/pri', label: 'PRI' },
  { to: '/learn', label: 'Learn' },
  { to: '/scenario-analyzer', label: 'Citizen Scenario Analyzer' },
];

type NavbarProps = {
  compact?: boolean;
};

export function Navbar({ compact = false }: NavbarProps) {
  return (
    <header className="sticky top-0 z-30 border-b border-amber-200/70 bg-white backdrop-blur-xl">
      <div className="flex w-full items-center justify-between gap-4 px-4 py-4 sm:px-6 lg:px-10">
        <Link to="/" className="group flex items-center gap-3">
          <div className="grid h-10 w-10 place-items-center rounded-2xl border border-electric/30 bg-electric/10 text-sm font-bold text-electric shadow-sm transition group-hover:border-electric/50">
            J
          </div>
          <div>
            <p className="text-base font-semibold text-slate-900">JurisCode Bharat</p>
            <p className="text-xs uppercase tracking-[0.3em] text-slate-500">AI Mock Trial Learning</p>
          </div>
        </Link>

        {!compact ? (
          <nav className="hidden items-center gap-2 lg:flex" aria-label="Primary navigation">
            {navItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  classNames(
                    'inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm transition',
                    isActive ? 'bg-amber-100/70 text-slate-900' : 'text-slate-700 hover:bg-amber-50/70 hover:text-slate-900',
                  )
                }
              >
                {item.to === '/scenario-analyzer' ? <MessageCircleIcon className="h-4 w-4 shrink-0 text-electric" /> : null}
                <span className={item.to === '/scenario-analyzer' ? 'max-w-[11rem] truncate sm:max-w-none' : undefined}>{item.label}</span>
              </NavLink>
            ))}
          </nav>
        ) : null}

        <div className="hidden items-center gap-3 md:flex">
          <span className="rounded-full border border-emeraldGlow/20 bg-emeraldGlow/10 px-3 py-1 text-xs font-medium text-emeraldGlow">
            Education-first AI
          </span>
          <span className="max-w-[18rem] rounded-full border border-mutedGold/20 bg-mutedGold/10 px-3 py-1 text-xs text-mutedGold">
            For educational and mock-trial practice purposes only. Not legal advice.
          </span>
        </div>
      </div>
    </header>
  );
}
