import { useTranslation } from 'react-i18next';
import { Field } from '../../../../../../components/ui/Field';
import { Input, Select, Textarea } from '../../../../../../components/ui/Input';
import type { FolioSchema } from '../../../../../../services/api/folio';
import { parseLabels, type Field as Name, type Metadata } from '../../validate';
import { DocketFields } from '../DocketFields';
import * as S from './style';

type Props = {
  value: Metadata;
  labelsText: string;
  onChange: (value: Metadata) => void;
  onLabelsText: (text: string) => void;
  onBlur: (field: Name) => void;
  schema: FolioSchema;
  /** Error message per field, already translated. */
  errors: Partial<Record<Name, string>>;
};

/** The publishing metadata: description, type, labels, owner, audiences and language, and
 * optionally the Docket project, milestones and areas the doc belongs to. */
export function MetadataForm({
  value,
  labelsText,
  onChange,
  onLabelsText,
  onBlur,
  schema,
  errors,
}: Props) {
  const { t } = useTranslation();
  const set = <K extends keyof Metadata>(key: K, next: Metadata[K]) =>
    onChange({ ...value, [key]: next });
  const length = value.description.trim().length;

  return (
    <S.Form>
      <Field
        label={t('folio.publish.description')}
        error={errors.description}
        hint={t('folio.publish.descriptionHint')}
      >
        <Textarea
          rows={3}
          value={value.description}
          invalid={Boolean(errors.description)}
          onChange={(e) => set('description', e.target.value)}
          onBlur={() => onBlur('description')}
        />
      </Field>
      <S.Count $bad={length > 0 && (length < 40 || length > 400)}>{length}/400</S.Count>
      <S.Row>
        <Field label={t('folio.publish.docType')} error={errors.doc_type}>
          <Select
            value={value.doc_type}
            invalid={Boolean(errors.doc_type)}
            onChange={(e) => set('doc_type', e.target.value)}
            onBlur={() => onBlur('doc_type')}
          >
            <option value="">{t('folio.publish.choose')}</option>
            {schema.doc_types.map((e) => (
              <option key={e.key} value={e.key}>
                {e.name}
              </option>
            ))}
          </Select>
        </Field>
        <Field label={t('folio.publish.language')} error={errors.language}>
          <Select
            value={value.language}
            invalid={Boolean(errors.language)}
            onChange={(e) => set('language', e.target.value)}
            onBlur={() => onBlur('language')}
          >
            <option value="">{t('folio.publish.choose')}</option>
            {schema.languages.map((e) => (
              <option key={e.key} value={e.key}>
                {e.name}
              </option>
            ))}
          </Select>
        </Field>
      </S.Row>
      <S.Row>
        <Field
          label={t('folio.publish.labels')}
          error={errors.labels}
          hint={t('folio.publish.labelsHint')}
        >
          <Input
            value={labelsText}
            invalid={Boolean(errors.labels)}
            onChange={(e) => {
              onLabelsText(e.target.value);
              set('labels', parseLabels(e.target.value));
            }}
            onBlur={() => onBlur('labels')}
          />
        </Field>
        <Field
          label={t('folio.publish.owner')}
          error={errors.owner}
          hint={t('folio.publish.ownerHint')}
        >
          <Input
            value={value.owner}
            invalid={Boolean(errors.owner)}
            onChange={(e) => set('owner', e.target.value.replace(/^@/, ''))}
            onBlur={() => onBlur('owner')}
          />
        </Field>
      </S.Row>
      <Field label={t('folio.publish.audiences')} error={errors.audiences} group>
        <S.Checks>
          {schema.audiences.map((e) => (
            <S.Check key={e.key}>
              <input
                type="checkbox"
                checked={value.audiences.includes(e.key)}
                onChange={(ev) => {
                  const rest = value.audiences.filter((a) => a !== e.key);
                  set('audiences', ev.target.checked ? [...rest, e.key] : rest);
                  onBlur('audiences');
                }}
              />
              {e.name}
            </S.Check>
          ))}
        </S.Checks>
      </Field>
      <DocketFields value={value} onChange={onChange} errors={errors} />
    </S.Form>
  );
}
