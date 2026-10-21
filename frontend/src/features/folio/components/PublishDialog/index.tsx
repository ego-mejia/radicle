import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '../../../../components/ui/Button';
import { Field, FormError } from '../../../../components/ui/Field';
import { Modal } from '../../../../components/ui/Modal';
import { PageSpinner } from '../../../../components/ui/Spinner';
import { Textarea } from '../../../../components/ui/Input';
import { useErrorMessage } from '../../../../hooks/useErrorMessage';
import { useMe } from '../../../../hooks/useMe';
import { isApiError } from '../../../../services/api/client';
import {
  fetchDraft,
  fetchMetadataSchema,
  folioKeys,
  publishNode,
  saveDraft,
  type FolioSchema,
  type FolioSubmission,
  type FolioVersion,
} from '../../../../services/api/folio';
import { AiSuggestions } from './components/AiSuggestions';
import { MetadataForm } from './components/MetadataForm';
import { fromDraft, validate, type Field as Name, type Metadata } from './validate';
import * as S from './style';

export type Published = FolioVersion | FolioSubmission;

type Props = {
  nodeId: string;
  title: string;
  /** The page's space: with the editor AI on there, empty fields get suggestions. */
  space?: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onPublished: (result: Published) => void;
};

/** Publish the draft: metadata prefilled from it, checked as you type, and a change note.
 * Agents send it for approval instead. */
export function PublishDialog(props: Props) {
  const { t } = useTranslation();
  const schema = useQuery({ queryKey: folioKeys.schema, queryFn: fetchMetadataSchema });
  const draft = useQuery({
    queryKey: folioKeys.draft(props.nodeId),
    queryFn: () => fetchDraft(props.nodeId),
    enabled: props.open,
  });
  return (
    <Modal
      open={props.open}
      onOpenChange={props.onOpenChange}
      title={t('folio.publish.title')}
      width={640}
    >
      {schema.data && draft.data ? (
        <Form {...props} schema={schema.data} initial={draft.data.metadata} />
      ) : (
        <PageSpinner />
      )}
    </Modal>
  );
}

function Form({
  nodeId,
  title,
  space,
  schema,
  initial,
  onPublished,
  onOpenChange,
}: Props & {
  schema: FolioSchema;
  initial: Record<string, unknown>;
}) {
  const { t } = useTranslation();
  const me = useMe();
  const queryClient = useQueryClient();
  const errorMessage = useErrorMessage();
  const [value, setValue] = useState<Metadata>(() => fromDraft(initial, me.handle));
  const [labelsText, setLabelsText] = useState(value.labels.join(', '));
  const [note, setNote] = useState('');
  const [touched, setTouched] = useState<Set<Name>>(new Set());
  const [server, setServer] = useState<Partial<Record<Name, string>>>({});
  const [conflict, setConflict] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const agent = me.kind === 'agent';

  const catalogs = useMemo(
    () => ({
      doc_types: schema.doc_types.map((e) => e.key),
      audiences: schema.audiences.map((e) => e.key),
      languages: schema.languages.map((e) => e.key),
    }),
    [schema],
  );
  const problems = validate(title, value, catalogs);
  const errors: Partial<Record<Name, string>> = {};
  for (const [field, key] of Object.entries(problems) as [Name, string][]) {
    if (touched.has(field)) errors[field] = t(`folio.publish.${key}`);
  }
  for (const [field, message] of Object.entries(server) as [Name, string][]) {
    errors[field] ??= message;
  }

  const submit = async (confirm = false) => {
    setTouched(new Set([...Object.keys(problems), ...touched] as Name[]));
    if (Object.keys(problems).length) return;
    setBusy(true);
    setFailure(null);
    setServer({});
    try {
      await saveDraft(nodeId, { metadata: value });
      const result = await publishNode(nodeId, { change_note: note.trim() || null, confirm });
      await queryClient.invalidateQueries({ queryKey: ['folio', 'nodes', nodeId] });
      onOpenChange(false);
      onPublished(result);
    } catch (error) {
      if (isApiError(error, 409)) setConflict(true);
      else if (isApiError(error, 422) && error.problem.errors.some((e) => e.field)) {
        setServer(Object.fromEntries(error.problem.errors.map((e) => [e.field, e.message])));
      } else setFailure(errorMessage(error));
    } finally {
      setBusy(false);
    }
  };

  return (
    <S.Body>
      {problems.title && <FormError>{t(`folio.publish.${problems.title}`)}</FormError>}
      {space && (
        <AiSuggestions
          nodeId={nodeId}
          space={space}
          value={value}
          schema={schema}
          onUse={(patch) => {
            setValue((v) => ({ ...v, ...patch }));
            if (patch.labels) setLabelsText(patch.labels.join(', '));
            setServer({});
          }}
        />
      )}
      <MetadataForm
        value={value}
        labelsText={labelsText}
        onChange={(next) => (setValue(next), setServer({}))}
        onLabelsText={setLabelsText}
        onBlur={(field) => setTouched((s) => new Set(s).add(field))}
        schema={schema}
        errors={errors}
      />
      <Field label={t('folio.publish.note')} hint={t('folio.publish.noteHint')}>
        <Textarea rows={2} value={note} onChange={(e) => setNote(e.target.value)} />
      </Field>
      {conflict && <FormError>{t('folio.publish.conflict')}</FormError>}
      {failure && <FormError>{failure}</FormError>}
      <S.Actions>
        {agent && <S.Note>{t('folio.publish.approvalNote')}</S.Note>}
        <Button onClick={() => onOpenChange(false)}>{t('folio.publish.cancel')}</Button>
        <Button variant="primary" disabled={busy} onClick={() => void submit(conflict)}>
          {conflict
            ? t('folio.publish.anyway')
            : agent
              ? t('folio.publish.sendForApproval')
              : t('folio.publish.publish')}
        </Button>
      </S.Actions>
    </S.Body>
  );
}
