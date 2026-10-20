import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '../../../../components/ui/Button';
import { Field, FormError } from '../../../../components/ui/Field';
import { Input } from '../../../../components/ui/Input';
import { SettingsCard } from '../../../../components/ui/SettingsCard';
import { PageSpinner } from '../../../../components/ui/Spinner';
import { useErrorMessage } from '../../../../hooks/useErrorMessage';
import { useToast } from '../../../../hooks/useToast';
import {
  type AssistantSettings as Settings,
  assistantKeys,
  fetchAssistantSettings,
  saveAssistantSettings,
  testAssistant,
} from '../../../../services/api/assistantAdmin';
import * as S from './style';

const PROVIDERS = ['none', 'anthropic', 'openai'] as const;
type Provider = (typeof PROVIDERS)[number];

function Form({ data }: { data: Settings }) {
  const { t } = useTranslation();
  const toast = useToast();
  const errorMessage = useErrorMessage();
  const queryClient = useQueryClient();
  const [provider, setProvider] = useState<Provider>(data.provider as Provider);
  const [model, setModel] = useState(data.model);
  const [baseUrl, setBaseUrl] = useState(data.base_url);
  const [key, setKey] = useState('');
  const locked = data.managed_by_env;
  const save = useMutation({
    mutationFn: (removeKey: boolean) =>
      saveAssistantSettings({
        provider,
        model,
        base_url: baseUrl,
        ...(removeKey ? { api_key: '' } : key ? { api_key: key } : {}),
      }),
    onSuccess: (next) => {
      queryClient.setQueryData(assistantKeys.settings, next);
      setKey('');
      toast(t('assistant.admin.saved'));
    },
  });
  const check = useMutation({ mutationFn: testAssistant });

  return (
    <S.Form
      onSubmit={(e) => {
        e.preventDefault();
        save.mutate(false);
      }}
    >
      {locked && <S.Banner>{t('assistant.admin.managedByEnv')}</S.Banner>}
      <Field label={t('assistant.admin.provider')} group>
        <S.Providers>
          {PROVIDERS.map((p) => (
            <S.Provider key={p} $active={provider === p}>
              <input
                type="radio"
                name="provider"
                checked={provider === p}
                disabled={locked}
                onChange={() => setProvider(p)}
              />
              <span>
                <b>{t(`assistant.admin.providers.${p}`)}</b>
                <small>{t(`assistant.admin.providerHints.${p}`)}</small>
              </span>
            </S.Provider>
          ))}
        </S.Providers>
      </Field>
      {provider !== 'none' && (
        <>
          <Field label={t('assistant.admin.model')} hint={t('assistant.admin.modelHint')}>
            <Input value={model} disabled={locked} onChange={(e) => setModel(e.target.value)} />
          </Field>
          <Field
            label={t('assistant.admin.baseUrl')}
            hint={t(`assistant.admin.baseUrlHint.${provider}`)}
          >
            <Input value={baseUrl} disabled={locked} onChange={(e) => setBaseUrl(e.target.value)} />
          </Field>
          <Field
            label={t('assistant.admin.apiKey')}
            hint={data.has_key ? t('assistant.admin.keySaved') : t('assistant.admin.keyHint')}
          >
            <Input
              type="password"
              autoComplete="off"
              value={key}
              disabled={locked}
              placeholder={data.has_key ? '••••••••' : ''}
              onChange={(e) => setKey(e.target.value)}
            />
          </Field>
        </>
      )}
      <FormError>{save.error ? errorMessage(save.error) : null}</FormError>
      {check.data && <S.Result $ok={check.data.ok}>{check.data.message}</S.Result>}
      <S.Actions>
        {!locked && (
          <Button type="submit" variant="primary" disabled={save.isPending}>
            {t('common.save')}
          </Button>
        )}
        {!locked && data.has_key && (
          <Button variant="ghost" onClick={() => save.mutate(true)}>
            {t('assistant.admin.removeKey')}
          </Button>
        )}
        <Button onClick={() => check.mutate()} disabled={check.isPending}>
          {t('assistant.admin.test')}
        </Button>
      </S.Actions>
    </S.Form>
  );
}

/** Admin → Settings: which LLM Radi uses. Without one he answers from the guide. */
export function AssistantSettings() {
  const { t } = useTranslation();
  const { data } = useQuery({ queryKey: assistantKeys.settings, queryFn: fetchAssistantSettings });
  return (
    <div data-tour="assistant.settings">
      <SettingsCard title={t('assistant.admin.title')} help={t('assistant.admin.help')}>
        {data ? <Form key={JSON.stringify(data)} data={data} /> : <PageSpinner />}
      </SettingsCard>
    </div>
  );
}
