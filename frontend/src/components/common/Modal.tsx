import type { ReactNode } from 'react';

type ModalProps = {
  open: boolean;
  title: string;
  children: ReactNode;
  onClose: () => void;
};

export function Modal({ open, title, children, onClose }: ModalProps) {
  if (!open) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center px-4">
      <button type="button" className="absolute inset-0 bg-white" aria-label="Close modal backdrop" onClick={onClose} />
      <div className="relative z-10 w-full max-w-3xl rounded-3xl border border-amber-200/70 bg-[#fffaf1] p-5 backdrop-blur-xl">
        <div className="flex items-start justify-between gap-4 border-b border-amber-200/70 pb-4">
          <h3 className="text-lg font-semibold text-slate-900">{title}</h3>
          <button
            type="button"
            onClick={onClose}
            className="rounded-full border border-amber-200/70 px-3 py-1 text-sm text-slate-700 transition hover:border-amber-300/70 hover:text-slate-900"
          >
            Close
          </button>
        </div>
        <div className="pt-4">{children}</div>
      </div>
    </div>
  );
}
