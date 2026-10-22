import { X } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import * as S from './style';

export type ActiveFilter = { key: string; label: string; onRemove: () => void };

type Props = { filters: ActiveFilter[]; summary: string; onClear?: () => void };

/** The filters a section table has on, each one removable, plus how many rows match. */
export function ActiveFilters({ filters, summary, onClear }: Props) {
  const { t } = useTranslation();
  if (!filters.length) return <S.Summary>{summary}</S.Summary>;
  return (
    <S.Row>
      {filters.map((f) => (
        <S.Chip key={f.key}>
          {f.label}
          <button
            type="button"
            aria-label={t('folio.filters.remove', { label: f.label })}
            onClick={f.onRemove}
          >
            <X aria-hidden />
          </button>
        </S.Chip>
      ))}
      <S.Summary>{summary}</S.Summary>
      {onClear ? (
        <S.Clear type="button" onClick={onClear}>
          {t('folio.filters.clear')}
        </S.Clear>
      ) : null}
    </S.Row>
  );
}
