import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { Field } from '../../../../../../components/ui/Field';
import { Input, Select } from '../../../../../../components/ui/Input';
import {
  fetchMetadataSchema,
  fetchSpaces,
  folioKeys,
  type SearchFilters as Filters,
} from '../../../../../../services/api/folio';
import * as S from './style';

type Props = { value: Filters; onChange: (filters: Filters) => void };

/** Narrow a search by space, kind, document type, label and language. */
export function SearchFilters({ value, onChange }: Props) {
  const { t } = useTranslation();
  const { data: spaces = [] } = useQuery({ queryKey: folioKeys.spaces, queryFn: fetchSpaces });
  const { data: schema } = useQuery({ queryKey: folioKeys.schema, queryFn: fetchMetadataSchema });
  const set = (key: keyof Filters, next: string) =>
    onChange({ ...value, [key]: next || undefined });
  const any = t('folio.searchPage.any');

  return (
    <S.Filters>
      <S.Legend>{t('folio.searchPage.filters')}</S.Legend>
      <Field label={t('folio.searchPage.space')}>
        <Select value={value.space ?? ''} onChange={(e) => set('space', e.target.value)}>
          <option value="">{any}</option>
          {spaces.map((s) => (
            <option key={s.key} value={s.key}>
              {s.name}
            </option>
          ))}
        </Select>
      </Field>
      <Field label={t('folio.searchPage.kind')}>
        <Select value={value.kind ?? ''} onChange={(e) => set('kind', e.target.value)}>
          <option value="">{any}</option>
          <option value="page">{t('folio.home.kinds.page')}</option>
          <option value="blog_post">{t('folio.home.kinds.blog_post')}</option>
        </Select>
      </Field>
      <Field label={t('folio.searchPage.docType')}>
        <Select value={value.doc_type ?? ''} onChange={(e) => set('doc_type', e.target.value)}>
          <option value="">{any}</option>
          {schema?.doc_types.map((d) => (
            <option key={d.key} value={d.key}>
              {d.name}
            </option>
          ))}
        </Select>
      </Field>
      <Field label={t('folio.searchPage.language')}>
        <Select value={value.language ?? ''} onChange={(e) => set('language', e.target.value)}>
          <option value="">{any}</option>
          {schema?.languages.map((l) => (
            <option key={l.key} value={l.key}>
              {l.name}
            </option>
          ))}
        </Select>
      </Field>
      <Field label={t('folio.searchPage.label')}>
        <Input
          value={value.label ?? ''}
          placeholder="onboarding"
          onChange={(e) => set('label', e.target.value)}
        />
      </Field>
    </S.Filters>
  );
}
