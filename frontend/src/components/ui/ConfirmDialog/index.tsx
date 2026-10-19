import { useTranslation } from 'react-i18next';
import { Button } from '../Button';
import { Modal } from '../Modal';

type Props = {
  open: boolean;
  title: string;
  message: string;
  confirmLabel: string;
  onConfirm: () => void;
  onCancel: () => void;
  danger?: boolean;
};

export function ConfirmDialog({
  open,
  title,
  message,
  confirmLabel,
  onConfirm,
  onCancel,
  danger = true,
}: Props) {
  const { t } = useTranslation();
  return (
    <Modal
      open={open}
      onOpenChange={(next) => !next && onCancel()}
      title={title}
      width={420}
      footer={
        <>
          <Button onClick={onCancel}>{t('common.cancel')}</Button>
          <Button variant={danger ? 'danger' : 'primary'} onClick={onConfirm} autoFocus>
            {confirmLabel}
          </Button>
        </>
      }
    >
      <p>{message}</p>
    </Modal>
  );
}
