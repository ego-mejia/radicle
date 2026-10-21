import { X } from 'lucide-react';
import { useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { IconButton } from '../../../../components/ui/Button';
import { DocsChat } from '../DocsChat';
import * as S from './style';

type Props = { open: boolean; onClose: () => void };

/** The docs chat beside any Folio page; `a` opens it, Escape closes it. */
export function ChatPanel({ open, onClose }: Props) {
  const { t } = useTranslation();

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, onClose]);

  // Kept mounted while closed so the conversation survives closing the panel.
  return (
    <S.Panel aria-label={t('folio.chat.title')} hidden={!open}>
      <S.Header>
        <h2>{t('folio.chat.title')}</h2>
        <IconButton label={t('folio.chat.close')} onClick={onClose}>
          <X aria-hidden />
        </IconButton>
      </S.Header>
      <S.Body>
        <DocsChat autoFocus={open} />
      </S.Body>
    </S.Panel>
  );
}
