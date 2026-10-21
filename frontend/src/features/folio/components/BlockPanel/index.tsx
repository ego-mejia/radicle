import { X } from 'lucide-react';
import { useEffect, type ReactNode } from 'react';
import { createPortal } from 'react-dom';
import { useTranslation } from 'react-i18next';
import { IconButton } from '../../../../components/ui/Button';
import * as S from './style';

type Props = {
  title: string;
  onClose: () => void;
  /** Wider for a visual: code and preview side by side. */
  wide?: boolean;
  children: ReactNode;
};

/** The editor's side panel for a block (Folio 3.3): it edits the block in place while
 * the page stays in view. Escape closes it. */
export function BlockPanel({ title, onClose, wide = false, children }: Props) {
  const { t } = useTranslation();
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose();
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  return createPortal(
    <S.Panel role="complementary" aria-label={title} $wide={wide}>
      <S.Header>
        <h2>{title}</h2>
        <IconButton label={t('folio.editor.panel.close')} onClick={onClose}>
          <X size={16} />
        </IconButton>
      </S.Header>
      <S.Body>{children}</S.Body>
    </S.Panel>,
    document.body,
  );
}
