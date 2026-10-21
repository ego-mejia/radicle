import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '../../../../../../components/ui/Button';
import { Input } from '../../../../../../components/ui/Input';
import * as S from './style';

type Props = {
  title: string;
  icon: string | null;
  onTitle: (title: string) => void;
  onIcon: (icon: string | null) => void;
  /** Enter in the title moves to the body. */
  onDone: () => void;
  /** Extra tools, like the cover button. */
  tools?: React.ReactNode;
};

/** The page's icon and title above the body. */
export function PageHeader({ title, icon, onTitle, onIcon, onDone, tools }: Props) {
  const { t } = useTranslation();
  const [choosing, setChoosing] = useState(false);
  const [draft, setDraft] = useState(icon ?? '');

  const pick = () => {
    onIcon(draft.trim() || null);
    setChoosing(false);
  };

  return (
    <S.Header>
      {icon && !choosing && (
        <S.Icon
          type="button"
          aria-label={t('folio.editor.changeIcon')}
          onClick={() => setChoosing(true)}
        >
          {icon}
        </S.Icon>
      )}
      {choosing ? (
        <S.Tools>
          <Input
            autoFocus
            maxLength={8}
            aria-label={t('folio.editor.icon')}
            placeholder={t('folio.editor.iconHint')}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') pick();
              if (e.key === 'Escape') setChoosing(false);
            }}
          />
          <Button size="sm" onClick={pick}>
            {t('folio.editor.save')}
          </Button>
          {icon && (
            <Button size="sm" variant="ghost" onClick={() => (onIcon(null), setChoosing(false))}>
              {t('folio.editor.removeIcon')}
            </Button>
          )}
        </S.Tools>
      ) : (
        <S.Tools>
          {!icon && (
            <Button size="sm" variant="ghost" onClick={() => setChoosing(true)}>
              {t('folio.editor.addIcon')}
            </Button>
          )}
          {tools}
        </S.Tools>
      )}
      <S.Title
        rows={1}
        aria-label={t('folio.editor.titleLabel')}
        placeholder={t('folio.editor.titlePlaceholder')}
        value={title}
        maxLength={200}
        onChange={(e) => onTitle(e.target.value.replace(/\n/g, ''))}
        onKeyDown={(e) => {
          if (e.key === 'Enter') {
            e.preventDefault();
            onDone();
          }
        }}
      />
    </S.Header>
  );
}
