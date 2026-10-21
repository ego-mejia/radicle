import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Check, Sparkles, X } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button, IconButton } from '../../../../components/ui/Button';
import { Field } from '../../../../components/ui/Field';
import { Input, Textarea } from '../../../../components/ui/Input';
import { SettingsCard, SettingsParts as P } from '../../../../components/ui/SettingsCard';
import { PageSpinner } from '../../../../components/ui/Spinner';
import { useErrorMessage } from '../../../../hooks/useErrorMessage';
import { useToast } from '../../../../hooks/useToast';
import {
  aiKeys,
  createGlossaryTerm,
  fetchGlossary,
  patchGlossaryTerm,
  suggestGlossaryTerms,
  type GlossaryStatus,
  type GlossaryTerm,
} from '../../../../services/api/folioAi';
import * as S from './style';

/** Folio, Admin, Glossary (Folio 4.6): approve or reject what the AI suggests from Verified
 * docs, and write terms by hand. Readers only ever see approved terms. */
export function GlossaryAdmin() {
  const { t } = useTranslation();
  const toast = useToast();
  const errorMessage = useErrorMessage();
  const client = useQueryClient();
  const suggested = useQuery({
    queryKey: aiKeys.glossary('suggested'),
    queryFn: () => fetchGlossary('suggested'),
  });
  const approved = useQuery({
    queryKey: aiKeys.glossary('approved'),
    queryFn: () => fetchGlossary('approved'),
  });
  const refresh = () => void client.invalidateQueries({ queryKey: ['folio', 'glossary'] });
  const failed = (e: unknown) => toast(errorMessage(e), 'error');
  const decide = useMutation({
    mutationFn: ({ id, status }: { id: string; status: GlossaryStatus }) =>
      patchGlossaryTerm(id, { status }),
    onSuccess: refresh,
    onError: failed,
  });
  const suggest = useMutation({
    mutationFn: suggestGlossaryTerms,
    onSuccess: (made) => {
      refresh();
      toast(t('folio.glossary.suggested', { count: made.length }));
    },
    onError: failed,
  });

  return (
    <>
      <SettingsCard
        title={t('folio.glossary.suggestions')}
        help={t('folio.glossary.suggestionsHelp')}
      >
        <P.Actions>
          <Button onClick={() => suggest.mutate()} disabled={suggest.isPending}>
            <Sparkles aria-hidden size={16} />
            {suggest.isPending ? t('folio.ai.thinking') : t('folio.glossary.suggest')}
          </Button>
        </P.Actions>
        {suggested.data ? (
          <P.Rows>
            {suggested.data.map((term) => (
              <TermRow key={term.id} term={term}>
                <IconButton
                  label={t('folio.glossary.approve', { term: term.term })}
                  onClick={() => decide.mutate({ id: term.id, status: 'approved' })}
                >
                  <Check />
                </IconButton>
                <IconButton
                  label={t('folio.glossary.reject', { term: term.term })}
                  onClick={() => decide.mutate({ id: term.id, status: 'rejected' })}
                >
                  <X />
                </IconButton>
              </TermRow>
            ))}
            {suggested.data.length === 0 && <P.Muted>{t('folio.glossary.noSuggestions')}</P.Muted>}
          </P.Rows>
        ) : (
          <PageSpinner />
        )}
      </SettingsCard>
      <SettingsCard title={t('folio.glossary.approved')} help={t('folio.glossary.approvedHelp')}>
        {approved.data ? (
          <P.Rows>
            {approved.data.map((term) => (
              <TermRow key={term.id} term={term}>
                <IconButton
                  label={t('folio.glossary.remove', { term: term.term })}
                  onClick={() => decide.mutate({ id: term.id, status: 'rejected' })}
                >
                  <X />
                </IconButton>
              </TermRow>
            ))}
            {approved.data.length === 0 && <P.Muted>{t('folio.glossary.none')}</P.Muted>}
            <AddTerm onAdded={refresh} />
          </P.Rows>
        ) : (
          <PageSpinner />
        )}
      </SettingsCard>
    </>
  );
}

function TermRow({ term, children }: { term: GlossaryTerm; children: React.ReactNode }) {
  const { t } = useTranslation();
  return (
    <P.Row>
      <S.Term>
        <strong>{term.term}</strong>
        {term.aliases.length > 0 && <small>{term.aliases.join(', ')}</small>}
        <p>{term.definition}</p>
        {term.source && <small>{t('folio.glossary.source', { title: term.source.title })}</small>}
      </S.Term>
      {children}
    </P.Row>
  );
}

function AddTerm({ onAdded }: { onAdded: () => void }) {
  const { t } = useTranslation();
  const toast = useToast();
  const errorMessage = useErrorMessage();
  const [term, setTerm] = useState('');
  const [aliases, setAliases] = useState('');
  const [definition, setDefinition] = useState('');
  const add = useMutation({
    mutationFn: () =>
      createGlossaryTerm({
        term: term.trim(),
        definition: definition.trim(),
        aliases: aliases
          .split(',')
          .map((a) => a.trim())
          .filter(Boolean),
      }),
    onSuccess: () => {
      setTerm('');
      setAliases('');
      setDefinition('');
      onAdded();
      toast(t('folio.glossary.added'));
    },
    onError: (e) => toast(errorMessage(e), 'error'),
  });
  const ready = term.trim() !== '' && definition.trim() !== '';
  return (
    <S.Form
      onSubmit={(e) => {
        e.preventDefault();
        if (ready) add.mutate();
      }}
    >
      <S.Pair>
        <Field label={t('folio.glossary.term')}>
          <Input value={term} onChange={(e) => setTerm(e.target.value)} />
        </Field>
        <Field label={t('folio.glossary.aliases')} hint={t('folio.glossary.aliasesHint')}>
          <Input value={aliases} onChange={(e) => setAliases(e.target.value)} />
        </Field>
      </S.Pair>
      <Field label={t('folio.glossary.definition')}>
        <Textarea rows={2} value={definition} onChange={(e) => setDefinition(e.target.value)} />
      </Field>
      <P.Actions>
        <Button type="submit" size="sm" variant="primary" disabled={!ready || add.isPending}>
          {t('folio.glossary.add')}
        </Button>
      </P.Actions>
    </S.Form>
  );
}
