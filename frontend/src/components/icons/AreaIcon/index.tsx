import { useTheme } from 'styled-components';
import { AREA_ICONS } from './icons';
import * as S from './style';

export { AREA_ICONS } from './icons';

type Props = {
  icon?: string | null;
  color?: string | null;
  size?: number;
  /** Shown on hover and read by screen readers; leave empty next to the area's name. */
  label?: string;
};

/** An area's icon in its color. Without an icon it is a small square of that color. */
export function AreaIcon({ icon, color, size = 14, label }: Props) {
  const theme = useTheme();
  const Icon = icon ? AREA_ICONS[icon] : undefined;
  // Drawn with the color itself, so menus that tint their icons grey do not repaint it.
  const tint = color ?? theme.color.textMuted;
  const a11y = label ? { role: 'img', 'aria-label': label, title: label } : { 'aria-hidden': true };
  return (
    <S.Wrap $color={tint} style={{ width: size, height: size }} {...a11y}>
      {Icon ? (
        <Icon width={size} height={size} strokeWidth={2.2} color={tint} />
      ) : (
        <S.Dot style={{ background: tint }} />
      )}
    </S.Wrap>
  );
}
