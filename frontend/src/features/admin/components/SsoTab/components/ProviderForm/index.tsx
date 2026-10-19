import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '../../../../../../components/ui/Button';
import { Field, FormError } from '../../../../../../components/ui/Field';
import { Input } from '../../../../../../components/ui/Input';
import type { ProviderInput } from '../../../../../../services/api/sso';
import * as S from './style';

export type ProviderValues = {
  name: string;
  issuer_url: string;
  client_id: string;
  allowed_domains: string[];
  auto_create_users: boolean;
  group_claim: string | null;
  group_mapping: Record<string, string>;
  enabled: boolean;
  has_secret?: boolean;
  redirect_uri?: string;
};

type Props = {
  initial?: ProviderValues;
  groupNames: Record<string, string>;
  pending: boolean;
  error: string | null;
  onSave: (body: ProviderInput) => void;
  onCancel?: () => void;
};

const lines = (text: string) =>
  text
    .split(/[\n,]/)
    .map((x) => x.trim())
    .filter(Boolean);

/** One OpenID Connect provider: issuer, client, domains and group mapping. */
export function ProviderForm({ initial, groupNames, pending, error, onSave, onCancel }: Props) {
  const { t } = useTranslation();
  const [name, setName] = useState(initial?.name ?? '');
  const [issuer, setIssuer] = useState(initial?.issuer_url ?? '');
  const [clientId, setClientId] = useState(initial?.client_id ?? '');
  const [secret, setSecret] = useState('');
  const [domains, setDomains] = useState((initial?.allowed_domains ?? []).join(', '));
  const [auto, setAuto] = useState(initial?.auto_create_users ?? true);
  const [claim, setClaim] = useState(initial?.group_claim ?? '');
  const [mapping, setMapping] = useState(
    Object.entries(initial?.group_mapping ?? {})
      .map(([k, v]) => `${k} = ${groupNames[v] ?? v}`)
      .join('\n'),
  );
  const [enabled, setEnabled] = useState(initial?.enabled ?? true);
  const submit = () => {
    const parsed: Record<string, string> = {};
    for (const line of mapping.split('\n')) {
      const [claimValue, group] = line.split('=').map((x) => x.trim());
      if (claimValue && group) parsed[claimValue] = group;
    }
    onSave({
      name,
      issuer_url: issuer,
      client_id: clientId,
      ...(secret ? { client_secret: secret } : {}),
      allowed_domains: lines(domains),
      auto_create_users: auto,
      group_claim: claim || null,
      group_mapping: parsed,
      enabled,
    });
  };
  return (
    <S.Form
      onSubmit={(e) => {
        e.preventDefault();
        submit();
      }}
    >
      <S.Grid>
        <Field label={t('sso.name')}>
          <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="Google" />
        </Field>
        <Field label={t('sso.issuer')} hint={t('sso.issuerHint')}>
          <Input
            value={issuer}
            onChange={(e) => setIssuer(e.target.value)}
            placeholder="https://accounts.google.com"
          />
        </Field>
        <Field label={t('sso.clientId')}>
          <Input value={clientId} onChange={(e) => setClientId(e.target.value)} />
        </Field>
        <Field
          label={t('sso.clientSecret')}
          hint={initial?.has_secret ? t('sso.secretSaved') : undefined}
        >
          <Input
            type="password"
            autoComplete="off"
            value={secret}
            onChange={(e) => setSecret(e.target.value)}
          />
        </Field>
        <Field label={t('sso.domains')} hint={t('sso.domainsHint')}>
          <Input
            value={domains}
            onChange={(e) => setDomains(e.target.value)}
            placeholder="acme.com"
          />
        </Field>
        <Field label={t('sso.groupClaim')} hint={t('sso.groupClaimHint')}>
          <Input value={claim} onChange={(e) => setClaim(e.target.value)} placeholder="groups" />
        </Field>
      </S.Grid>
      <Field label={t('sso.mapping')} hint={t('sso.mappingHint')}>
        <S.Mapping
          rows={3}
          value={mapping}
          onChange={(e) => setMapping(e.target.value)}
          placeholder="radicle-backend = backend"
        />
      </Field>
      <S.Row>
        <label>
          <input type="checkbox" checked={auto} onChange={(e) => setAuto(e.target.checked)} />
          {t('sso.autoCreate')}
        </label>
        <label>
          <input type="checkbox" checked={enabled} onChange={(e) => setEnabled(e.target.checked)} />
          {t('sso.enabled')}
        </label>
      </S.Row>
      {initial?.redirect_uri && (
        <S.Redirect>
          {t('sso.redirect')} <code>{initial.redirect_uri}</code>
        </S.Redirect>
      )}
      <FormError>{error}</FormError>
      <S.Row>
        <Button
          type="submit"
          variant="primary"
          disabled={pending || !name || !issuer || !clientId || (!initial && !secret)}
        >
          {t('common.save')}
        </Button>
        {onCancel && <Button onClick={onCancel}>{t('common.cancel')}</Button>}
      </S.Row>
    </S.Form>
  );
}
