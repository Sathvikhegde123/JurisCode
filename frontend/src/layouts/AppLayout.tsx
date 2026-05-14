import type { ReactNode } from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import { Footer } from '@/components/layout/Footer';
import { Navbar } from '@/components/layout/Navbar';
import { classNames } from '@/utils/classNames';

type AppLayoutProps = {
  children?: ReactNode;
};

const bottomNavItems = [
  { to: '/dashboard', label: 'Home' },
  { to: '/practice', label: 'Practice' },
  { to: '/challenge', label: 'Challenge' },
  { to: '/learn', label: 'Learn' },
];

export function AppLayout({ children }: AppLayoutProps) {
  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,_rgba(249,115,22,0.16),_transparent_30%),radial-gradient(circle_at_top_right,_rgba(34,197,94,0.12),_transparent_30%),linear-gradient(180deg,_#fffaf3_0%,_#f7f1e3_100%)] text-slate-900">
      <Navbar />
      <div className="flex w-full">
        <div className="flex min-h-[calc(100vh-73px)] flex-1 flex-col">
          <main className={classNames('flex-1 px-4 py-6 pb-24 sm:px-6 lg:px-10 page-fade')}>{children ?? <Outlet />}</main>
          <Footer />
        </div>
      </div>

      <nav className="fixed inset-x-0 bottom-0 z-30 border-t border-amber-200/70 bg-white px-3 py-2 backdrop-blur-xl xl:hidden" aria-label="Bottom navigation">
        <div className="mx-auto grid max-w-3xl grid-cols-4 gap-2">
          {bottomNavItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                classNames(
                  'rounded-2xl border px-3 py-2 text-center text-xs transition',
                  isActive
                    ? 'border-electric/30 bg-electric/15 text-slate-900'
                    : 'border-amber-200/70 bg-white text-slate-700 hover:border-electric/30 hover:text-slate-900',
                )
              }
            >
              {item.label}
            </NavLink>
          ))}
        </div>
      </nav>
    </div>
  );
}
