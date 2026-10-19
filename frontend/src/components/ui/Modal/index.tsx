import * as Dialog from '@radix-ui/react-dialog';
import { X } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { IconButton } from '../Button';
import * as S from './style';

type Props = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
  width?: number;
};

export function Modal({ open, onOpenChange, title, children, footer, width = 520 }: Props) {
  const { t } = useTranslation();
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <S.Overlay />
        <S.Content $width={width} aria-describedby={undefined}>
          <S.Header>
            <S.Title>{title}</S.Title>
            <Dialog.Close asChild>
              <IconButton label={t('common.close')}>
                <X />
              </IconButton>
            </Dialog.Close>
          </S.Header>
          <S.Body>{children}</S.Body>
          {footer && <S.Footer>{footer}</S.Footer>}
        </S.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

type PanelProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  children: React.ReactNode;
};

/** Right-hand side panel, used to open a ticket over the board or list. */
export function SidePanel({ open, onOpenChange, title, children }: PanelProps) {
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <S.Overlay />
        <S.Panel aria-describedby={undefined}>
          <S.HiddenTitle>{title}</S.HiddenTitle>
          {children}
        </S.Panel>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
