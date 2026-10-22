import { X } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import * as S from './style';

type Props = {
  title: string;
  text: React.ReactNode;
  /** Links or buttons; the first is the main one. */
  actions: React.ReactNode;
  onDismiss: () => void;
};

/** A suggestion from Radi inside a page (RAD-57, board R, option 1): a dark card with his
 * face, so it never reads as part of the content. */
export function RadiSuggestion({ title, text, actions, onDismiss }: Props) {
  const { t } = useTranslation();
  return (
    <S.Card aria-label={t('folio.radi.suggestion')}>
      <S.Face aria-hidden>
        <svg viewBox="0 0 26 26" width="26" height="26">
          <ellipse cx="9" cy="12" rx="2.6" ry="4" />
          <ellipse cx="17" cy="12" rx="2.6" ry="4" />
        </svg>
      </S.Face>
      <S.Say>
        <S.Kicker>{t('folio.radi.suggestion')}</S.Kicker>
        <span>
          <strong>{title}</strong> {text}
        </span>
      </S.Say>
      <S.Actions>
        {actions}
        <S.Dismiss type="button" aria-label={t('folio.radi.dismiss')} onClick={onDismiss}>
          <X aria-hidden />
        </S.Dismiss>
      </S.Actions>
    </S.Card>
  );
}
