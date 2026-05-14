import { createContext, useContext, useMemo, useState, type ReactNode } from 'react';
import { classNames } from '@/utils/classNames';

type ToastVariant = 'success' | 'error' | 'info';

type Toast = {
  id: string;
  title: string;
  message?: string;
  variant: ToastVariant;
};

type ToastInput = Omit<Toast, 'id'>;

type ToastContextValue = {
  notify: (toast: ToastInput) => void;
  dismiss: (id: string) => void;
};

const ToastContext = createContext<ToastContextValue | null>(null);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const dismiss = (id: string) => {
    setToasts((current) => current.filter((toast) => toast.id !== id));
  };

  const notify = (toast: ToastInput) => {
    const id = crypto.randomUUID();
    setToasts((current) => [{ ...toast, id }, ...current].slice(0, 4));
    window.setTimeout(() => dismiss(id), 4200);
  };

  const value = useMemo(
    () => ({ notify, dismiss }),
    [],
  );

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="pointer-events-none fixed right-4 top-4 z-50 flex w-[calc(100vw-2rem)] max-w-sm flex-col gap-3 sm:right-6 sm:top-6">
        {toasts.map((toast) => (
          <div
            key={toast.id}
            role="status"
            className={classNames(
              'pointer-events-auto rounded-2xl border border-white/10 bg-charcoal/90 p-4 text-sm shadow-glow backdrop-blur-xl transition duration-200',
              toast.variant === 'success' && 'shadow-[0_0_0_1px_rgba(16,185,129,0.2)]',
              toast.variant === 'error' && 'shadow-[0_0_0_1px_rgba(239,68,68,0.2)]',
              toast.variant === 'info' && 'shadow-[0_0_0_1px_rgba(59,130,246,0.2)]',
            )}
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="font-semibold text-white">{toast.title}</p>
                {toast.message ? <p className="mt-1 text-slate-300">{toast.message}</p> : null}
              </div>
              <button
                type="button"
                onClick={() => dismiss(toast.id)}
                className="rounded-full border border-white/10 px-2 py-1 text-xs text-slate-300 transition hover:border-white/20 hover:text-white"
              >
                Close
              </button>
            </div>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error('useToast must be used within ToastProvider');
  }

  return context;
}
