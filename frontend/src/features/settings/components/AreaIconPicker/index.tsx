import * as Popover from '@radix-ui/react-popover';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { AREA_ICONS, AreaIcon } from '../../../../components/icons/AreaIcon';
import * as S from './style';

type Props = {
  area: string;
  icon: string | null;
  color: string | null;
  onPick: (icon: string | null) => void;
};

/** A button with the area's icon that opens a grid of icons, drawn in the area's color. */
export function AreaIconPicker({ area, icon, color, onPick }: Props) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const pick = (value: string | null) => {
    setOpen(false);
    if (value !== icon) onPick(value);
  };
  return (
    <Popover.Root open={open} onOpenChange={setOpen}>
      <Popover.Trigger asChild>
        <S.Trigger type="button" aria-label={t('settings.areaIcon', { name: area })}>
          <AreaIcon icon={icon} color={color} size={18} />
        </S.Trigger>
      </Popover.Trigger>
      <Popover.Portal>
        <S.Content align="start" sideOffset={4} aria-label={t('settings.areaIcon', { name: area })}>
          <S.Grid role="listbox" aria-label={t('settings.icons')}>
            {Object.keys(AREA_ICONS).map((name) => (
              <S.Choice
                key={name}
                type="button"
                role="option"
                aria-selected={name === icon}
                $active={name === icon}
                title={name}
                aria-label={name}
                onClick={() => pick(name)}
              >
                <AreaIcon icon={name} color={color} size={18} />
              </S.Choice>
            ))}
          </S.Grid>
          <S.None type="button" onClick={() => pick(null)} disabled={icon === null}>
            {t('settings.noIcon')}
          </S.None>
        </S.Content>
      </Popover.Portal>
    </Popover.Root>
  );
}
