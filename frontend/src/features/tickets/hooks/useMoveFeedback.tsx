import { useTranslation } from 'react-i18next';
import { Button } from '../../../components/ui/Button';
import { useErrorMessage } from '../../../hooks/useErrorMessage';
import { useToast } from '../../../hooks/useToast';
import { ApiError } from '../../../services/api/client';
import type { Ticket } from '../../../services/api/types';
import { announceDone } from '../../milestones/lib/celebrate';

/**
 * Toasts after a status change: warnings (blocked, forced), the exact rules that failed,
 * and a Force button for admins when the blocked policy stops the move.
 */
export function useMoveFeedback() {
  const { t } = useTranslation();
  const toast = useToast();
  const errorMessage = useErrorMessage();
  return {
    warnings(ticket: Ticket) {
      // Every successful move lands here: the last ticket of a milestone starts the party.
      announceDone(ticket);
      for (const w of ticket.warnings ?? []) {
        const keys = (w.by ?? []).join(', ');
        const text =
          w.code === 'blocked'
            ? t('ticket.warningBlocked', { keys })
            : w.code === 'forced'
              ? t('ticket.warningForced', { keys })
              : w.message;
        toast(text, 'warning');
      }
    },
    error(error: unknown, retryWithForce?: () => void) {
      if (error instanceof ApiError && error.problem.failed_rules?.length) {
        const lines = error.problem.failed_rules.map((f) => `• ${f.message}`);
        toast([t('ticket.rulesFailed'), ...lines].join('\n'), 'error');
        return;
      }
      if (error instanceof ApiError && error.problem.can_force && retryWithForce) {
        toast(
          error.message,
          'error',
          <Button size="sm" variant="danger" onClick={retryWithForce}>
            {t('ticket.force')}
          </Button>,
        );
        return;
      }
      toast(errorMessage(error), 'error');
    },
  };
}
