import { X } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { IconButton } from '../Button';
import * as S from './style';

export type ToastTone = 'info' | 'error' | 'warning';
export type ToastMessage = { id: number; text: string; tone: ToastTone; action?: React.ReactNode };

type Props = { toasts: ToastMessage[]; onDismiss: (id: number) => void };

export function ToastRegion({ toasts, onDismiss }: Props) {
  const { t } = useTranslation();
  return (
    <S.Region role="status" aria-live="polite">
      {toasts.map((toast) => (
        <S.Item key={toast.id} $tone={toast.tone}>
          <S.Text>{toast.text}</S.Text>
          {toast.action}
          <IconButton label={t('common.close')} onClick={() => onDismiss(toast.id)}>
            <X />
          </IconButton>
        </S.Item>
      ))}
    </S.Region>
  );
}
