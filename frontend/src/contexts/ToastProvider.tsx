import { useCallback, useRef, useState } from 'react';
import { ToastRegion, type ToastMessage, type ToastTone } from '../components/ui/Toast';
import { ToastContext } from './toast';

const DURATION_MS = 5000;

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<ToastMessage[]>([]);
  const nextId = useRef(1);

  const dismiss = useCallback((id: number) => {
    setToasts((current) => current.filter((toast) => toast.id !== id));
  }, []);

  const show = useCallback(
    (text: string, tone: ToastTone = 'info', action?: React.ReactNode) => {
      const id = nextId.current++;
      setToasts((current) => [...current.slice(-3), { id, text, tone, action }]);
      window.setTimeout(() => dismiss(id), DURATION_MS);
    },
    [dismiss],
  );

  return (
    <ToastContext.Provider value={show}>
      {children}
      <ToastRegion toasts={toasts} onDismiss={dismiss} />
    </ToastContext.Provider>
  );
}
