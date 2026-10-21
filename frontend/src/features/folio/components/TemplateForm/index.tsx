import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link } from '@tanstack/react-router';
import { ArrowLeft } from 'lucide-react';
import { lazy, Suspense, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '../../../../components/ui/Button';
import { Field, FormError } from '../../../../components/ui/Field';
import { Input, Select, Textarea } from '../../../../components/ui/Input';
import { PageTitle } from '../../../../components/ui/PageTitle';
import { useErrorMessage } from '../../../../hooks/useErrorMessage';
import { useToast } from '../../../../hooks/useToast';
import {
  fetchMetadataSchema,
  folioKeys,
  updateTemplate,
  type FolioTemplate,
} from '../../../../services/api/folio';
import { TEMPLATE_VARIABLES } from '../TemplatesAdmin/variables';
import { useAutosave } from '../../hooks/useAutosave';
import * as S from './style';

// TipTap loads only when a template is opened.
const TemplateBody = lazy(() =>
  import('../TemplateBody').then((m) => ({ default: m.TemplateBody })),
);

/** A template's name, icon, document type and default labels, and its document (page
 * templates) or tree of pages (space templates). */
export function TemplateForm({ template }: { template: FolioTemplate }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const toast = useToast();
  const errorMessage = useErrorMessage();
  const { data: schema } = useQuery({ queryKey: folioKeys.schema, queryFn: fetchMetadataSchema });
  const [name, setName] = useState(template.name);
  const [description, setDescription] = useState(template.description);
  const [icon, setIcon] = useState(template.icon ?? '');
  const [docType, setDocType] = useState(template.doc_type_key ?? '');
  const labels = (template.default_metadata.labels as string[] | undefined) ?? [];
  const [labelText, setLabelText] = useState(labels.join(', '));
  const [structure, setStructure] = useState(JSON.stringify(template.structure ?? {}, null, 2));
  const [structureError, setStructureError] = useState<string | null>(null);

  // The PATCH replaces every field, so each save sends the whole form.
  const fields = () => {
    let parsed: Record<string, unknown> | null = null;
    if (template.kind === 'space') parsed = JSON.parse(structure) as Record<string, unknown>;
    return {
      name,
      description,
      icon: icon.trim() || null,
      doc_type_key: docType || null,
      default_metadata: {
        ...template.default_metadata,
        labels: labelText
          .split(',')
          .map((l) => l.trim().replace(/^#/, '').toLowerCase())
          .filter(Boolean),
      },
      structure: parsed,
    };
  };
  const body = useAutosave(async (doc: Record<string, unknown>) => {
    const saved = await updateTemplate(template.id, { ...fields(), content_json: doc });
    queryClient.setQueryData(folioKeys.template(saved.id), saved);
  });
  const save = useMutation({
    mutationFn: () => updateTemplate(template.id, fields()),
    onSuccess: (saved) => {
      queryClient.setQueryData(folioKeys.template(saved.id), saved);
      void queryClient.invalidateQueries({ queryKey: ['folio', 'templates'] });
      toast(t('folio.templates.saved'));
    },
    onError: (e) =>
      e instanceof SyntaxError
        ? setStructureError(t('folio.templates.badJson'))
        : toast(errorMessage(e), 'error'),
  });

  return (
    <>
      <S.Back as={Link} to="/folio/admin">
        <ArrowLeft aria-hidden size={16} />
        {t('folio.templates.back')}
      </S.Back>
      <PageTitle title={template.name} subtitle={t(`folio.templates.kinds.${template.kind}`)} />
      <S.Form
        onSubmit={(e) => {
          e.preventDefault();
          setStructureError(null);
          save.mutate();
        }}
      >
        <S.Row>
          <Field label={t('folio.templates.icon')}>
            <Input value={icon} onChange={(e) => setIcon(e.target.value)} maxLength={8} />
          </Field>
          <Field label={t('folio.templates.name')}>
            <Input value={name} onChange={(e) => setName(e.target.value)} required />
          </Field>
        </S.Row>
        <Field label={t('folio.templates.description')}>
          <Textarea value={description} onChange={(e) => setDescription(e.target.value)} />
        </Field>
        {template.kind === 'page' && (
          <S.Row>
            <Field label={t('folio.templates.docType')}>
              <Select value={docType} onChange={(e) => setDocType(e.target.value)}>
                <option value="">{t('folio.templates.noDocType')}</option>
                {schema?.doc_types.map((d) => (
                  <option key={d.key} value={d.key}>
                    {d.name}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label={t('folio.templates.labels')} hint={t('folio.publish.labelsHint')}>
              <Input value={labelText} onChange={(e) => setLabelText(e.target.value)} />
            </Field>
          </S.Row>
        )}
        {template.kind === 'page' ? (
          <S.Body>
            <S.Variables>
              {t('folio.templates.variables', TEMPLATE_VARIABLES)}
              <S.State role="status">
                {t(`folio.editor.state.${body.state === 'unsaved' ? 'saving' : body.state}`)}
              </S.State>
            </S.Variables>
            <Suspense fallback={null}>
              <TemplateBody content={template.content_json} onChange={body.change} />
            </Suspense>
          </S.Body>
        ) : (
          <Field
            label={t('folio.templates.structure')}
            hint={t('folio.templates.structureHint')}
            error={structureError}
          >
            <S.Code value={structure} onChange={(e) => setStructure(e.target.value)} rows={16} />
          </Field>
        )}
        <FormError>
          {save.error && !(save.error instanceof SyntaxError) ? errorMessage(save.error) : null}
        </FormError>
        <S.Actions>
          <Button type="submit" variant="primary" disabled={!name.trim() || save.isPending}>
            {t('folio.templates.save')}
          </Button>
        </S.Actions>
      </S.Form>
    </>
  );
}
