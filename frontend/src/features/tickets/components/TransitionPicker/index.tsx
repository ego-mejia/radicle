import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { CategoryIcon } from '../../../../components/icons/CategoryIcon';
import { Button } from '../../../../components/ui/Button';
import type { Resolution, TransitionOption } from '../../../../services/api/types';
import * as S from './style';

export type Pick = { option: TransitionOption; resolution: Resolution | null };

type Props = {
  options: TransitionOption[];
  onPick: (pick: Pick) => void;
  /** Preselect a transition, e.g. after a drop, so only the resolution is asked. */
  initial?: TransitionOption | null;
};

/**
 * Lists transitions; a done target with several allowed resolutions asks which one.
 * A single allowed resolution is applied directly, like the API does.
 */
export function TransitionPicker({ options, onPick, initial = null }: Props) {
  const { t } = useTranslation();
  const [pending, setPending] = useState<TransitionOption | null>(initial);

  if (options.length === 0) return <S.Empty>{t('ticket.noTransitions')}</S.Empty>;

  const choose = (option: TransitionOption) => {
    const resolutions = option.allowed_resolutions ?? [];
    if (option.category !== 'done' || resolutions.length <= 1) {
      onPick({ option, resolution: resolutions[0] ?? null });
    } else {
      setPending(option);
    }
  };

  return (
    <S.List role="menu">
      {options.map((option) => (
        <S.Option
          key={`${option.name}-${option.to_status}`}
          role="menuitem"
          $selected={pending === option}
          onClick={() => choose(option)}
        >
          <CategoryIcon category={option.category} />
          {option.to_status}
          <S.Via>{option.name}</S.Via>
        </S.Option>
      ))}
      {pending && (
        <S.Resolutions>
          <strong>{t('ticket.pickResolution', { status: pending.to_status })}</strong>
          <S.Chips>
            {(pending.allowed_resolutions ?? []).map((resolution) => (
              <Button
                key={resolution}
                size="sm"
                onClick={() => onPick({ option: pending, resolution })}
              >
                {t(`ticket.resolutions.${resolution}`)}
              </Button>
            ))}
          </S.Chips>
        </S.Resolutions>
      )}
    </S.List>
  );
}
