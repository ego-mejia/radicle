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
  type AiProvider,
  type AiSettings,
  aiKeys,
  fetchAiSettings,
  saveAiSettings,
  testAi,
} from '../../../../services/api/ai';
import * as S from './style';

const PROVIDERS: AiProvider[] = ['none', 'openai', 'openai_compatible', 'ollama', 'anthropic'];

function Form({ data }: { data: AiSettings }) {
  const { t } = useTranslation();
  const toast = useToast();
  const errorMessage = useErrorMessage();
  const queryClient = useQueryClient();
  const [provider, setProvider] = useState<AiProvider>(data.provider);
  const [chatModel, setChatModel] = useState(data.chat_model);
  const [embeddingModel, setEmbeddingModel] = useState(data.embedding_model);
  const [dimensions, setDimensions] = useState(data.embedding_dimensions?.toString() ?? '');
  const [baseUrl, setBaseUrl] = useState(data.base_url);
  const [key, setKey] = useState('');
  const save = useMutation({
    mutationFn: (removeKey: boolean) =>
      saveAiSettings({
        provider,
        chat_model: chatModel,
        embedding_model: embeddingModel,
        embedding_dimensions: dimensions ? Number(dimensions) : null,
        base_url: baseUrl,
        ...(removeKey ? { api_key: '' } : key ? { api_key: key } : {}),
      }),
    onSuccess: (next) => {
      queryClient.setQueryData(aiKeys.settings, next);
      setKey('');
      toast(t('aiProvider.saved'));
    },
  });
  const check = useMutation({ mutationFn: testAi });

  return (
    <S.Form
      onSubmit={(e) => {
        e.preventDefault();
        save.mutate(false);
      }}
    >
      <Field label={t('aiProvider.provider')} group>
        <S.Providers>
          {PROVIDERS.map((p) => (
            <S.Provider key={p} $active={provider === p}>
              <input
                type="radio"
                name="ai-provider"
                checked={provider === p}
                onChange={() => setProvider(p)}
              />
              <span>
                <b>{t(`aiProvider.providers.${p}`)}</b>
                <small>{t(`aiProvider.providerHints.${p}`)}</small>
              </span>
            </S.Provider>
          ))}
        </S.Providers>
      </Field>
      {provider !== 'none' && (
        <>
          <Field label={t('aiProvider.chatModel')}>
            <Input value={chatModel} onChange={(e) => setChatModel(e.target.value)} />
          </Field>
          <Field label={t('aiProvider.embeddingModel')} hint={t('aiProvider.embeddingHint')}>
            <Input value={embeddingModel} onChange={(e) => setEmbeddingModel(e.target.value)} />
          </Field>
          <Field label={t('aiProvider.dimensions')} hint={t('aiProvider.dimensionsHint')}>
            <Input
              type="number"
              min={1}
              value={dimensions}
              onChange={(e) => setDimensions(e.target.value)}
            />
          </Field>
          <Field label={t('aiProvider.baseUrl')} hint={t(`aiProvider.baseUrlHint.${provider}`)}>
            <Input value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)} />
          </Field>
          <Field
            label={t('aiProvider.apiKey')}
            hint={data.has_key ? t('aiProvider.keySaved') : t('aiProvider.keyHint')}
          >
            <Input
              type="password"
              autoComplete="off"
              value={key}
              placeholder={data.has_key ? '••••••••' : ''}
              onChange={(e) => setKey(e.target.value)}
            />
          </Field>
        </>
      )}
      <FormError>{save.error ? errorMessage(save.error) : null}</FormError>
      {check.data && <S.Result $ok={check.data.ok}>{check.data.message}</S.Result>}
      <S.Actions>
        <Button type="submit" variant="primary" disabled={save.isPending}>
          {t('common.save')}
        </Button>
        {data.has_key && (
          <Button variant="ghost" onClick={() => save.mutate(true)}>
            {t('aiProvider.removeKey')}
          </Button>
        )}
        <Button onClick={() => check.mutate()} disabled={check.isPending}>
          {t('aiProvider.test')}
        </Button>
      </S.Actions>
    </S.Form>
  );
}

/** Admin → Settings: the AI provider every app shares for chat and embeddings. */
export function AiProviderSettings() {
  const { t } = useTranslation();
  const { data } = useQuery({ queryKey: aiKeys.settings, queryFn: fetchAiSettings });
  return (
    <SettingsCard title={t('aiProvider.title')} help={t('aiProvider.help')}>
      {data ? <Form key={JSON.stringify(data)} data={data} /> : <PageSpinner />}
    </SettingsCard>
  );
}
