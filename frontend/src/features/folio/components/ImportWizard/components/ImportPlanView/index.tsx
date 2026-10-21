import { useMutation, useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Badge } from '../../../../../../components/ui/Badge';
import { Button } from '../../../../../../components/ui/Button';
import { Field } from '../../../../../../components/ui/Field';
import { Input, Select } from '../../../../../../components/ui/Input';
import { SettingsCard } from '../../../../../../components/ui/SettingsCard';
import { useErrorMessage } from '../../../../../../hooks/useErrorMessage';
import { fetchMetadataSchema, folioKeys } from '../../../../../../services/api/folio';
import { fetchPeople } from '../../../../../../services/api/folioComments';
import {
  dryRunImport,
  type FolioImport,
  type ImportPlan,
  type ImportPlanPage,
  runImport,
} from '../../../../../../services/api/folioImports';
import * as S from './style';

type Props = { item: FolioImport; onChange: (item: FolioImport) => void };
type Defaults = { doc_type: string; language: string; audience: string; description: string };

function depths(pages: ImportPlanPage[]): Map<string, number> {
  const parent = new Map(pages.map((p) => [p.external_id, p.parent_id]));
  const out = new Map<string, number>();
  for (const p of pages) {
    let depth = 0;
    let at = p.parent_id;
    while (at && depth < 10) {
      depth += 1;
      at = parent.get(at) ?? null;
    }
    out.set(p.external_id, depth);
  }
  return out;
}

/** Step 2: the dry run. Who each author becomes, metadata to publish complete pages with,
 * and every page with what will happen to it. Check again as often as needed, then run. */
export function ImportPlanView({ item, onChange }: Props) {
  const { t } = useTranslation();
  const errorMessage = useErrorMessage();
  const plan = item.report as ImportPlan;
  const { data: people } = useQuery({
    queryKey: ['folio', 'people', ''],
    queryFn: () => fetchPeople(),
  });
  const { data: schema } = useQuery({ queryKey: folioKeys.schema, queryFn: fetchMetadataSchema });
  const [authors, setAuthors] = useState<Record<string, string>>(() =>
    Object.fromEntries(plan.authors.map((a) => [a.source, a.user?.handle ?? ''])),
  );
  const [defaults, setDefaults] = useState<Defaults>({
    doc_type: '',
    language: '',
    audience: '',
    description: '',
  });
  const options = () => {
    const meta = Object.fromEntries(
      Object.entries({
        doc_type: defaults.doc_type,
        language: defaults.language,
        audiences: defaults.audience ? [defaults.audience] : '',
        description: defaults.description.trim(),
      }).filter(([, v]) => v),
    );
    return {
      authors: Object.fromEntries(Object.entries(authors).map(([k, v]) => [k, v || null])),
      default_metadata: Object.keys(meta).length ? meta : null,
    };
  };
  const check = useMutation({
    mutationFn: () => dryRunImport(item.id, options()),
    onSuccess: (next) => onChange(next),
  });
  const run = useMutation({
    mutationFn: async () => runImport((await dryRunImport(item.id, options())).id),
    onSuccess: (next) => onChange(next),
  });
  const level = depths(plan.pages);
  const set = (key: keyof Defaults) => (e: { target: { value: string } }) =>
    setDefaults((d) => ({ ...d, [key]: e.target.value }));
  const error = check.error ?? run.error;

  return (
    <>
      <S.Totals>
        {(['pages', 'folders', 'databases', 'attachments', 'updates', 'with_errors'] as const).map(
          (k) => (
            <div key={k}>
              <strong>{plan.totals[k]}</strong>
              <span>{t(`folio.imports.totals.${k}`)}</span>
            </div>
          ),
        )}
      </S.Totals>
      {plan.errors.map((e) => (
        <S.Problem key={e} role="alert">
          {e}
        </S.Problem>
      ))}
      {plan.authors.length > 0 && (
        <SettingsCard title={t('folio.imports.authors')} help={t('folio.imports.authorsHelp')}>
          <S.Rows>
            {plan.authors.map((a) => (
              <S.Row key={a.source}>
                <span>{a.source}</span>
                <Select
                  aria-label={t('folio.imports.authorOf', { name: a.source })}
                  value={authors[a.source] ?? ''}
                  onChange={(e) => setAuthors((m) => ({ ...m, [a.source]: e.target.value }))}
                >
                  <option value="">{t('folio.imports.nobody')}</option>
                  {(people ?? []).map((p) => (
                    <option key={p.handle} value={p.handle}>
                      {p.name} (@{p.handle})
                    </option>
                  ))}
                </Select>
              </S.Row>
            ))}
          </S.Rows>
        </SettingsCard>
      )}
      <SettingsCard title={t('folio.imports.defaults')} help={t('folio.imports.defaultsHelp')}>
        <S.Grid>
          <Field label={t('folio.reader.meta.docType')}>
            <Select value={defaults.doc_type} onChange={set('doc_type')}>
              <option value="">—</option>
              {schema?.doc_types.map((d) => (
                <option key={d.key} value={d.key}>
                  {d.name}
                </option>
              ))}
            </Select>
          </Field>
          <Field label={t('folio.reader.meta.audiences')}>
            <Select value={defaults.audience} onChange={set('audience')}>
              <option value="">—</option>
              {schema?.audiences.map((d) => (
                <option key={d.key} value={d.key}>
                  {d.name}
                </option>
              ))}
            </Select>
          </Field>
          <Field label={t('folio.reader.meta.language')}>
            <Select value={defaults.language} onChange={set('language')}>
              <option value="">—</option>
              {schema?.languages.map((d) => (
                <option key={d.key} value={d.key}>
                  {d.name}
                </option>
              ))}
            </Select>
          </Field>
        </S.Grid>
        <Field label={t('folio.imports.description')}>
          <Input value={defaults.description} onChange={set('description')} />
        </Field>
      </SettingsCard>
      <SettingsCard title={t('folio.imports.pages')}>
        <S.Table>
          <thead>
            <tr>
              <th>{t('folio.imports.page')}</th>
              <th>{t('folio.imports.action')}</th>
              <th>{t('folio.imports.labels')}</th>
              <th>{t('folio.imports.files')}</th>
            </tr>
          </thead>
          <tbody>
            {plan.pages.map((p) => (
              <tr key={p.external_id}>
                <S.Title $depth={level.get(p.external_id) ?? 0}>
                  {p.title}
                  {p.kind !== 'page' && <small> · {t(`folio.imports.kinds.${p.kind}`)}</small>}
                  {p.errors.map((e) => (
                    <S.PageError key={e}>{e}</S.PageError>
                  ))}
                </S.Title>
                <td>
                  <Badge tone={p.action === 'update' ? 'warning' : 'accent'}>
                    {t(`folio.imports.actions.${p.action}`)}
                  </Badge>
                </td>
                <td>{p.labels.join(', ')}</td>
                <td>
                  {p.kind === 'database'
                    ? t('folio.imports.rows', { count: p.rows })
                    : p.attachments}
                </td>
              </tr>
            ))}
          </tbody>
        </S.Table>
      </SettingsCard>
      {error && <S.Problem role="alert">{errorMessage(error)}</S.Problem>}
      <S.Actions>
        <Button onClick={() => check.mutate()} disabled={check.isPending}>
          {t('folio.imports.checkAgain')}
        </Button>
        <Button
          variant="primary"
          onClick={() => run.mutate()}
          disabled={run.isPending || plan.pages.length === 0}
        >
          {t('folio.imports.run', { count: plan.pages.length })}
        </Button>
      </S.Actions>
    </>
  );
}
