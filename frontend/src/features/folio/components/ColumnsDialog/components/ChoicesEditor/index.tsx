import { Plus, X } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Button, IconButton } from '../../../../../../components/ui/Button';
import { Input, Select } from '../../../../../../components/ui/Input';
import {
  CHOICE_COLORS,
  type ChoiceColor,
  type DbChoice,
} from '../../../../../../services/api/folioDatabases';
import { Choice } from '../../../DbValue';
import * as S from '../../style';

type Props = { choices: DbChoice[]; onChange: (choices: DbChoice[]) => void };

/** A select's choices: a value and a color each. Removing one clears it from the rows. */
export function ChoicesEditor({ choices, onChange }: Props) {
  const { t } = useTranslation();
  const set = (i: number, patch: Partial<DbChoice>) =>
    onChange(choices.map((c, j) => (j === i ? { ...c, ...patch } : c)));
  return (
    <S.Choices aria-label={t('folio.db.choices')}>
      {choices.map((c, i) => (
        <S.Line key={i}>
          <Input
            aria-label={t('folio.db.choiceValue')}
            value={c.value}
            maxLength={100}
            onChange={(e) => set(i, { value: e.target.value })}
          />
          <Select
            aria-label={t('folio.db.choiceColor')}
            value={c.color}
            onChange={(e) => set(i, { color: e.target.value as ChoiceColor })}
          >
            {CHOICE_COLORS.map((color) => (
              <option key={color} value={color}>
                {t(`folio.db.color.${color}`)}
              </option>
            ))}
          </Select>
          <Choice
            column={{ key: '', name: '', type: 'select', options: { choices } }}
            value={c.value}
          />
          <IconButton
            label={t('folio.db.removeChoice', { choice: c.value })}
            onClick={() => onChange(choices.filter((_, j) => j !== i))}
          >
            <X />
          </IconButton>
        </S.Line>
      ))}
      <Button
        size="sm"
        variant="ghost"
        onClick={() => onChange([...choices, { value: '', color: 'grey' }])}
      >
        <Plus aria-hidden />
        {t('folio.db.addChoice')}
      </Button>
    </S.Choices>
  );
}
