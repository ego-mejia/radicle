import { useMutation } from '@tanstack/react-query';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '../../../../components/ui/Button';
import { Field } from '../../../../components/ui/Field';
import { Input, Textarea } from '../../../../components/ui/Input';
import { Modal } from '../../../../components/ui/Modal';
import { Tabs } from '../../../../components/ui/Tabs';
import { useErrorMessage } from '../../../../hooks/useErrorMessage';
import { shareNode, type ShareResult } from '../../../../services/api/folioWork';
import { PublicLink } from './components/PublicLink';
import * as S from './style';

type Props = {
  nodeId: string;
  title: string;
  /** The page's space, to share it whole too. */
  space?: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
};

const list = (text: string) =>
  text
    .split(/[,\s]+/)
    .map((v) => v.trim())
    .filter(Boolean);

/** Send a page to people and groups with a message, optionally letting them in; or give
 * the page or its space a public link. */
export function ShareDialog({ nodeId, title, space, open, onOpenChange }: Props) {
  const { t } = useTranslation();
  const [tab, setTab] = useState<'people' | 'public'>('people');
  const errorMessage = useErrorMessage();
  const [users, setUsers] = useState('');
  const [groups, setGroups] = useState('');
  const [message, setMessage] = useState('');
  const [grantView, setGrantView] = useState(false);
  const [result, setResult] = useState<ShareResult | null>(null);
  const share = useMutation({
    mutationFn: () =>
      shareNode(nodeId, {
        users: list(users),
        groups: list(groups),
        message,
        grant_view: grantView,
      }),
    onSuccess: setResult,
  });

  const close = (next: boolean) => {
    onOpenChange(next);
    if (!next) {
      setResult(null);
      share.reset();
    }
  };
  const empty = !list(users).length && !list(groups).length;

  return (
    <Modal
      open={open}
      onOpenChange={close}
      title={t('folio.share.title', { title })}
      footer={
        result || tab === 'public' ? (
          <Button variant="primary" onClick={() => close(false)}>
            {t('folio.share.done')}
          </Button>
        ) : (
          <>
            <Button onClick={() => close(false)}>{t('folio.share.cancel')}</Button>
            <Button
              variant="primary"
              disabled={empty || share.isPending}
              onClick={() => share.mutate()}
            >
              {t('folio.share.send')}
            </Button>
          </>
        )
      }
    >
      <Tabs
        label={t('folio.share.tabs')}
        value={tab}
        onChange={setTab}
        tabs={[
          { id: 'people', label: t('folio.share.people') },
          { id: 'public', label: t('folio.share.public.tab') },
        ]}
      />
      {tab === 'public' ? (
        <S.Form>
          <PublicLink target={{ node: nodeId }} label={t('folio.share.public.page')} />
          {space && <PublicLink target={{ space }} label={t('folio.share.public.space')} />}
        </S.Form>
      ) : result ? (
        <S.Result role="status">
          <p>
            {result.notified.length
              ? t('folio.share.sent', { names: result.notified.map((h) => `@${h}`).join(', ') })
              : t('folio.share.nobody')}
          </p>
          {result.granted.length > 0 && (
            <p>{t('folio.share.granted', { names: result.granted.join(', ') })}</p>
          )}
          {result.cannot_see.length > 0 && (
            <S.Warn>
              {t('folio.share.cannotSee', {
                names: result.cannot_see.map((h) => `@${h}`).join(', '),
              })}
            </S.Warn>
          )}
        </S.Result>
      ) : (
        <S.Form>
          <Field label={t('folio.share.users')} hint={t('folio.share.usersHint')}>
            <Input
              value={users}
              onChange={(e) => setUsers(e.target.value)}
              placeholder="@ana, @luis"
            />
          </Field>
          <Field label={t('folio.share.groups')}>
            <Input value={groups} onChange={(e) => setGroups(e.target.value)} />
          </Field>
          <Field label={t('folio.share.message')}>
            <Textarea rows={3} value={message} onChange={(e) => setMessage(e.target.value)} />
          </Field>
          <S.Check>
            <input
              type="checkbox"
              checked={grantView}
              onChange={(e) => setGrantView(e.target.checked)}
            />
            {t('folio.share.grantView')}
          </S.Check>
          {share.error && <S.Error role="alert">{errorMessage(share.error)}</S.Error>}
        </S.Form>
      )}
    </Modal>
  );
}
