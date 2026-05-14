import type { ReactNode } from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import { Footer } from '@/components/layout/Footer';
import { Navbar } from '@/components/layout/Navbar';
import { Sidebar } from '@/components/layout/Sidebar';
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
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,_rgba(59,130,246,0.16),_transparent_24%),radial-gradient(circle_at_top_right,_rgba(16,185,129,0.12),_transparent_28%),linear-gradient(180deg,_#07111f_0%,_#050a12_100%)] text-white">
      <Navbar compact />
      <div className="mx-auto flex max-w-7xl">
        <Sidebar />
        <div className="flex min-h-[calc(100vh-73px)] flex-1 flex-col">
          <main className={classNames('flex-1 px-4 py-6 pb-24 sm:px-6 lg:px-8 xl:px-10')}>{children ?? <Outlet />}</main>
          <Footer />
        </div>
      </div>

      <nav className="fixed inset-x-0 bottom-0 z-30 border-t border-white/10 bg-[#07111fe6] px-3 py-2 backdrop-blur-xl xl:hidden" aria-label="Bottom navigation">
        <div className="mx-auto grid max-w-3xl grid-cols-4 gap-2">
          {bottomNavItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                classNames(
                  'rounded-2xl border px-3 py-2 text-center text-xs transition',
                  isActive
                    ? 'border-electric/30 bg-electric/15 text-white'
                    : 'border-white/10 bg-white/5 text-slate-300 hover:border-electric/30 hover:text-white',
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
