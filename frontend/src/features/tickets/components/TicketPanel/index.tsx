import { Link } from '@tanstack/react-router';
import { Maximize2, X } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { IconButton } from '../../../../components/ui/Button';
import { SidePanel } from '../../../../components/ui/Modal';
import { TicketDetail } from '../TicketDetail';
import * as S from './style';

type Props = { ticketKey: string | undefined; onClose: () => void };

/** Ticket detail sliding in from the right, over the board or list. */
export function TicketPanel({ ticketKey, onClose }: Props) {
  const { t } = useTranslation();
  return (
    <SidePanel
      open={!!ticketKey}
      onOpenChange={(open) => !open && onClose()}
      title={ticketKey ?? ''}
    >
      {ticketKey && (
        <>
          <S.Bar>
            <Link to="/t/$key" params={{ key: ticketKey }} aria-label={ticketKey}>
              <IconButton label={t('common.seeAll')} tabIndex={-1}>
                <Maximize2 />
              </IconButton>
            </Link>
            <IconButton label={t('common.close')} onClick={onClose}>
              <X />
            </IconButton>
          </S.Bar>
          <S.Body>
            <TicketDetail key={ticketKey} ticketKey={ticketKey} />
          </S.Body>
        </>
      )}
    </SidePanel>
  );
}
