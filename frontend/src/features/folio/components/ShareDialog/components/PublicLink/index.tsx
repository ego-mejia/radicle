import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Copy, Link2Off } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '../../../../../../components/ui/Button';
import { useErrorMessage } from '../../../../../../hooks/useErrorMessage';
import { useToast } from '../../../../../../hooks/useToast';
import { isApiError } from '../../../../../../services/api/client';
import {
  createPublicLink,
  fetchPublicLinks,
  publicKeys,
  revokePublicLink,
} from '../../../../../../services/api/folioPublic';
import * as S from './style';

type Props = {
  /** A page's link, or (with `space`) the whole space's. */
  target: { node: string } | { space: string };
  label: string;
};

/** One public link: create it (hidden from search engines by default), copy it, or
 * revoke it. Only the space's admins get past the first request. */
export function PublicLink({ target, label }: Props) {
  const { t } = useTranslation();
  const toast = useToast();
  const errorMessage = useErrorMessage();
  const client = useQueryClient();
  const [noindex, setNoindex] = useState(true);
  const key = publicKeys.links(target);
  const links = useQuery({ queryKey: key, queryFn: () => fetchPublicLinks(target) });
  const kind = 'node' in target ? 'node' : 'space';
  const link = links.data?.find((l) => l.target_type === kind);
  const refresh = () => client.invalidateQueries({ queryKey: key });
  const onError = (e: unknown) => toast(errorMessage(e), 'error');
  const create = useMutation({
    mutationFn: () => createPublicLink({ ...target, noindex }),
    onSuccess: refresh,
    onError,
  });
  const revoke = useMutation({
    mutationFn: (id: string) => revokePublicLink(id),
    onSuccess: () => {
      toast(t('folio.share.public.revoked'));
      return refresh();
    },
    onError,
  });

  if (links.isPending) return null;
  if (links.isError)
    return (
      <S.Note>
        {isApiError(links.error, 403)
          ? t('folio.share.public.adminsOnly')
          : errorMessage(links.error)}
      </S.Note>
    );

  return (
    <S.Box aria-label={label} role="group">
      <S.Label>{label}</S.Label>
      {link ? (
        <>
          <S.Row>
            <S.Url readOnly value={link.url} aria-label={t('folio.share.public.url')} />
            <Button
              onClick={async () => {
                await navigator.clipboard.writeText(link.url);
                toast(t('folio.share.public.copied'));
              }}
            >
              <Copy aria-hidden size={14} />
              {t('folio.share.public.copy')}
            </Button>
            <Button
              variant="danger"
              disabled={revoke.isPending}
              onClick={() => revoke.mutate(link.id)}
            >
              <Link2Off aria-hidden size={14} />
              {t('folio.share.public.revoke')}
            </Button>
          </S.Row>
          <S.Note>
            {t('folio.share.public.views', { count: link.view_count })}
            {link.noindex && ` · ${t('folio.share.public.hidden')}`}
          </S.Note>
        </>
      ) : (
        <S.Row>
          <S.Check>
            <input
              type="checkbox"
              checked={noindex}
              onChange={(e) => setNoindex(e.target.checked)}
            />
            {t('folio.share.public.noindex')}
          </S.Check>
          <Button variant="primary" disabled={create.isPending} onClick={() => create.mutate()}>
            {t('folio.share.public.create')}
          </Button>
        </S.Row>
      )}
    </S.Box>
  );
}
