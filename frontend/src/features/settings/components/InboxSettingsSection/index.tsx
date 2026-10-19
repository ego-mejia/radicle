import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Copy, ExternalLink } from 'lucide-react';
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '../../../../components/ui/Button';
import { Field, FormError } from '../../../../components/ui/Field';
import { Input, Select, Textarea } from '../../../../components/ui/Input';
import { SettingsCard } from '../../../../components/ui/SettingsCard';
import { PageSpinner } from '../../../../components/ui/Spinner';
import { useErrorMessage } from '../../../../hooks/useErrorMessage';
import { useToast } from '../../../../hooks/useToast';
import {
  fetchInboxSettings,
  type InboxSettingsPatch,
  putInboxSettings,
} from '../../../../services/api/inbox';
import type { ProjectDetail } from '../../../../services/api/types';
import * as S from './style';

const KINDS = ['complaint', 'suggestion', 'idea'] as const;
const key = (project: string) => ['inbox-settings', project] as const;

/** The public form: on/off, address, texts, kinds, email, files, captcha and tags. */
export function InboxSettingsSection({
  project,
  editable,
}: {
  project: ProjectDetail;
  editable: boolean;
}) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const toast = useToast();
  const errorMessage = useErrorMessage();
  const { data } = useQuery({
    queryKey: key(project.key),
    queryFn: () => fetchInboxSettings(project.key),
  });
  const [draft, setDraft] = useState<InboxSettingsPatch>({});
  useEffect(() => {
    if (data) setDraft({});
  }, [data]);
  const save = useMutation({
    mutationFn: () => putInboxSettings(project.key, draft),
    onSuccess: (next) => {
      queryClient.setQueryData(key(project.key), next);
      toast(t('inboxSettings.saved'));
    },
  });
  if (!data) return <PageSpinner />;
  const value = <K extends keyof InboxSettingsPatch>(k: K) =>
    (draft[k] ?? (data as Record<string, unknown>)[k]) as NonNullable<InboxSettingsPatch[K]>;
  const set = (patch: InboxSettingsPatch) => setDraft((d) => ({ ...d, ...patch }));
  const kinds = value('allowed_classifications');
  const url = data.public_url;
  return (
    <SettingsCard title={t('inboxSettings.title')} help={t('inboxSettings.help')}>
      <S.Form
        onSubmit={(e) => {
          e.preventDefault();
          save.mutate();
        }}
      >
        <S.Check>
          <input
            type="checkbox"
            checked={value('enabled')}
            disabled={!editable}
            onChange={(e) => set({ enabled: e.target.checked })}
          />
          {t('inboxSettings.enabled')}
        </S.Check>
        <S.Link>
          <code>{url}</code>
          <Button
            size="sm"
            variant="ghost"
            onClick={() =>
              void navigator.clipboard?.writeText(url).then(() => toast(t('inboxSettings.copied')))
            }
          >
            <Copy />
            {t('inboxSettings.copy')}
          </Button>
          <a href={url} target="_blank" rel="noreferrer">
            <ExternalLink size={14} /> {t('inboxSettings.open')}
          </a>
        </S.Link>
        <S.Grid>
          <Field label={t('inboxSettings.slug')} hint="/b/…">
            <Input
              value={value('public_slug')}
              disabled={!editable}
              onChange={(e) => set({ public_slug: e.target.value })}
            />
          </Field>
          <Field label={t('inboxSettings.pageTitle')}>
            <Input
              value={value('title')}
              disabled={!editable}
              onChange={(e) => set({ title: e.target.value })}
            />
          </Field>
        </S.Grid>
        <Field label={t('inboxSettings.intro')}>
          <Textarea
            rows={3}
            value={value('intro_md')}
            disabled={!editable}
            onChange={(e) => set({ intro_md: e.target.value })}
          />
        </Field>
        <Field label={t('inboxSettings.thanks')}>
          <Textarea
            rows={2}
            value={value('thank_you_md')}
            disabled={!editable}
            onChange={(e) => set({ thank_you_md: e.target.value })}
          />
        </Field>
        <Field label={t('inboxSettings.kinds')} group>
          <S.Row>
            {KINDS.map((k) => (
              <S.Check key={k}>
                <input
                  type="checkbox"
                  checked={kinds.includes(k)}
                  disabled={!editable}
                  onChange={(e) =>
                    set({
                      allowed_classifications: e.target.checked
                        ? [...kinds, k]
                        : kinds.filter((x) => x !== k),
                    })
                  }
                />
                {t(`inbox.classifications.${k}`)}
              </S.Check>
            ))}
          </S.Row>
        </Field>
        <S.Row>
          <S.Check>
            <input
              type="checkbox"
              checked={value('require_email')}
              disabled={!editable}
              onChange={(e) => set({ require_email: e.target.checked })}
            />
            {t('inboxSettings.requireEmail')}
          </S.Check>
          <S.Check>
            <input
              type="checkbox"
              checked={value('allow_attachments')}
              disabled={!editable}
              onChange={(e) => set({ allow_attachments: e.target.checked })}
            />
            {t('inboxSettings.attachments')}
          </S.Check>
        </S.Row>
        <S.Grid>
          <Field label={t('inboxSettings.maxFiles')}>
            <Input
              type="number"
              min={0}
              max={5}
              value={value('max_attachments')}
              disabled={!editable}
              onChange={(e) => set({ max_attachments: Number(e.target.value) })}
            />
          </Field>
          <Field label={t('inboxSettings.tags')} hint={t('inboxSettings.tagsHint')}>
            <Input
              value={value('auto_tags').join(', ')}
              disabled={!editable}
              onChange={(e) =>
                set({
                  auto_tags: e.target.value
                    .split(',')
                    .map((x) => x.trim())
                    .filter(Boolean),
                })
              }
            />
          </Field>
          <Field label={t('inboxSettings.captcha')} hint={t('inboxSettings.captchaHint')}>
            <Select
              value={value('captcha')}
              disabled={!editable}
              onChange={(e) => set({ captcha: e.target.value })}
            >
              <option value="altcha">ALTCHA</option>
              <option value="turnstile">Cloudflare Turnstile</option>
              <option value="hcaptcha">hCaptcha</option>
              <option value="none">{t('inboxSettings.noCaptcha')}</option>
            </Select>
          </Field>
        </S.Grid>
        {(value('captcha') === 'turnstile' || value('captcha') === 'hcaptcha') && (
          <S.Grid>
            <Field label={t('inboxSettings.siteKey')}>
              <Input
                value={draft.captcha_site_key ?? data.captcha_site_key ?? ''}
                disabled={!editable}
                onChange={(e) => set({ captcha_site_key: e.target.value })}
              />
            </Field>
            <Field
              label={t('inboxSettings.secret')}
              hint={data.captcha_has_secret ? t('inboxSettings.secretSaved') : undefined}
            >
              <Input
                type="password"
                autoComplete="off"
                value={draft.captcha_secret ?? ''}
                disabled={!editable}
                onChange={(e) => set({ captcha_secret: e.target.value })}
              />
            </Field>
          </S.Grid>
        )}
        <FormError>{save.error ? errorMessage(save.error) : null}</FormError>
        {editable && (
          <Button
            type="submit"
            variant="primary"
            disabled={save.isPending || Object.keys(draft).length === 0}
          >
            {t('common.save')}
          </Button>
        )}
      </S.Form>
    </SettingsCard>
  );
}
