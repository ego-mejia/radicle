import { useTranslation } from 'react-i18next';
import { Badge } from '../../../../components/ui/Badge';
import type { FolioNode } from '../../../../services/api/folio';
import * as S from './style';

type Props = {
  metadata: Record<string, unknown> | null | undefined;
  status: FolioNode['status'];
  version: number | null;
};

const list = (value: unknown): string[] =>
  Array.isArray(value) ? value.map(String).filter(Boolean) : [];

/** The page's metadata as the reader sees it: who owns it, its state and its catalogs. */
export function PageMeta({ metadata, status, version }: Props) {
  const { t } = useTranslation();
  const m = metadata ?? {};
  const owner = m.owner ? String(m.owner) : null;
  const labels = list(m.labels);
  const audiences = list(m.audiences);
  const rows: [string, React.ReactNode][] = [
    [t('folio.reader.meta.owner'), owner ? `@${owner}` : '—'],
    [
      t('folio.reader.meta.status'),
      <Badge
        key="status"
        tone={status === 'verified' ? 'accent' : status === 'outdated' ? 'warning' : 'neutral'}
      >
        {t(`folio.reader.status.${status}`)}
      </Badge>,
    ],
  ];
  if (m.doc_type) rows.push([t('folio.reader.meta.docType'), String(m.doc_type)]);
  if (m.language) rows.push([t('folio.reader.meta.language'), String(m.language)]);
  if (version) rows.push([t('folio.reader.meta.version'), `v${version}`]);
  if (audiences.length) rows.push([t('folio.reader.meta.audiences'), audiences.join(', ')]);

  return (
    <S.Card aria-label={t('folio.reader.meta.title')}>
      <S.Rows>
        {rows.map(([label, value]) => (
          <S.Row key={label}>
            <dt>{label}</dt>
            <dd>{value}</dd>
          </S.Row>
        ))}
      </S.Rows>
      {labels.length > 0 && (
        <S.Labels aria-label={t('folio.reader.meta.labels')}>
          {labels.map((label) => (
            <li key={label}>#{label}</li>
          ))}
        </S.Labels>
      )}
    </S.Card>
  );
}
