import * as Dropdown from '@radix-ui/react-dropdown-menu';
import * as S from './style';

export type MenuItem = {
  key: string;
  label: React.ReactNode;
  onSelect: () => void;
  icon?: React.ReactNode;
  hint?: React.ReactNode;
  danger?: boolean;
  disabled?: boolean;
};

type Props = {
  trigger: React.ReactNode;
  items: (MenuItem | { separator: true; key: string } | { label: string; key: string })[];
  align?: 'start' | 'end';
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
};

export function Menu({ trigger, items, align = 'start', open, onOpenChange }: Props) {
  return (
    <Dropdown.Root open={open} onOpenChange={onOpenChange}>
      <Dropdown.Trigger asChild>{trigger}</Dropdown.Trigger>
      <Dropdown.Portal>
        <S.Content align={align} sideOffset={4}>
          {items.map((item) => {
            if ('separator' in item) return <S.Separator key={item.key} />;
            if (!('onSelect' in item)) return <S.Label key={item.key}>{item.label}</S.Label>;
            return (
              <S.Item
                key={item.key}
                $danger={item.danger}
                disabled={item.disabled}
                onSelect={item.onSelect}
              >
                {item.icon}
                {item.label}
                {item.hint && <S.Hint>{item.hint}</S.Hint>}
              </S.Item>
            );
          })}
        </S.Content>
      </Dropdown.Portal>
    </Dropdown.Root>
  );
}
