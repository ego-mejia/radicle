import { Plus } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { PALETTE } from '../../state';
import * as S from './style';

/** The block types to add; each lands at the bottom of the grid. */
export function BlockPalette({ onAdd }: { onAdd: (type: string) => void }) {
  const { t } = useTranslation();
  const label = t('folio.homeEditor.palette');
  return (
    <S.Palette aria-label={label}>
      <S.Label>{label}</S.Label>
      {PALETTE.map((type) => (
        <S.Item key={type} type="button" onClick={() => onAdd(type)}>
          <Plus aria-hidden />
          {t(`folio.homeEditor.types.${type}`)}
        </S.Item>
      ))}
    </S.Palette>
  );
}
