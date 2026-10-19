import { useTranslation } from 'react-i18next';
import { Modal } from '../../../../components/ui/Modal';
import type { TicketType, TransitionOption } from '../../../../services/api/types';
import { TransitionPicker, type Pick } from '../../../tickets/components/TransitionPicker';

type Props = {
  ticketKey: string;
  ticketType: TicketType;
  options: TransitionOption[];
  onPick: (pick: Pick) => void;
  onCancel: () => void;
};

/** Shown after a drop when the column has several transitions or needs a resolution. */
export function DropResolver({ ticketKey, ticketType, options, onPick, onCancel }: Props) {
  const { t } = useTranslation();
  return (
    <Modal
      open
      onOpenChange={(open) => !open && onCancel()}
      title={t('board.chooseTransition', { key: ticketKey })}
      width={380}
    >
      <TransitionPicker
        options={options}
        onPick={onPick}
        initial={options.length === 1 ? options[0] : null}
        projectKey={ticketKey.split('-')[0]}
        ticketType={ticketType}
      />
    </Modal>
  );
}
