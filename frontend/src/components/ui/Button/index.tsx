import { forwardRef } from 'react';
import { Base, Icon, type Size, type Variant } from './style';

type Props = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: Variant;
  size?: Size;
  block?: boolean;
};

export const Button = forwardRef<HTMLButtonElement, Props>(function Button(
  { variant = 'secondary', size = 'md', block = false, type = 'button', ...rest },
  ref,
) {
  return <Base ref={ref} type={type} $variant={variant} $size={size} $block={block} {...rest} />;
});

type IconProps = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  label: string;
  active?: boolean;
};

/** Square icon-only button; `label` is required for screen readers and the tooltip. */
export const IconButton = forwardRef<HTMLButtonElement, IconProps>(function IconButton(
  { label, active = false, type = 'button', ...rest },
  ref,
) {
  return <Icon ref={ref} type={type} aria-label={label} title={label} $active={active} {...rest} />;
});
