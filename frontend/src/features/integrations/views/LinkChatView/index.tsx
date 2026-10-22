import { useMutation } from '@tanstack/react-query';
import { useSearch } from '@tanstack/react-router';
import { useTranslation } from 'react-i18next';
import { Button } from '../../../../components/ui/Button';
import { FormError } from '../../../../components/ui/Field';
import { PageTitle } from '../../../../components/ui/PageTitle';
import { useErrorMessage } from '../../../../hooks/useErrorMessage';
import { linkChatAccount } from '../../../../services/api/integrations';
import * as S from './style';

/** The page /radicle links to: confirm you are that Slack or Teams user (Folio 5.4). */
export function LinkChatView() {
  const { t } = useTranslation();
  const { token = '' } = useSearch({ from: '/app/integrations/link' });
  const errorMessage = useErrorMessage();
  const link = useMutation({ mutationFn: () => linkChatAccount(token) });
  return (
    <>
      <PageTitle title={t('integrations.linkTitle')} />
      <S.Box>
        {link.data ? (
          <p role="status">{t('integrations.linked', { name: link.data.integration })}</p>
        ) : (
          <>
            <p>{t('integrations.linkHelp')}</p>
            <FormError>{link.error ? errorMessage(link.error) : null}</FormError>
            <div>
              <Button
                variant="primary"
                disabled={!token || link.isPending}
                onClick={() => link.mutate()}
              >
                {t('integrations.linkConfirm')}
              </Button>
            </div>
          </>
        )}
      </S.Box>
    </>
  );
}
