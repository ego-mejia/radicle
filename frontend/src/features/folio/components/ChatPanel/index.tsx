import { X } from 'lucide-react';
import { useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { IconButton } from '../../../../components/ui/Button';
import { DocsChat } from '../DocsChat';
import * as S from './style';

type Props = {
  open: boolean;
  onClose: () => void;
  /** Told while an answer is on its way, so Radi can look busy. */
  onPending?: (pending: boolean) => void;
};

/** Radi in Folio (RAD-57): the docs chat beside any Folio page, answering only from the
 * docs you can see, with its sources and the tools it used. `a` opens it, Escape closes it. */
export function ChatPanel({ open, onClose, onPending }: Props) {
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
        <S.Who>
          <h2>{t('folio.radi.name')}</h2>
          <small>{t('folio.radi.subtitle')}</small>
        </S.Who>
        <IconButton label={t('folio.chat.close')} onClick={onClose}>
          <X aria-hidden />
        </IconButton>
      </S.Header>
      <S.Body>
        <DocsChat autoFocus={open} tools onPending={onPending} />
      </S.Body>
    </S.Panel>
  );
}
