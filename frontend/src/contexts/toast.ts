import { createContext } from 'react';
import type { ToastTone } from '../components/ui/Toast';

export type ShowToast = (text: string, tone?: ToastTone, action?: React.ReactNode) => void;

export const ToastContext = createContext<ShowToast | null>(null);
