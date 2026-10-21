import { Link } from '@tanstack/react-router';
import { useTranslation } from 'react-i18next';
import { Badge } from '../../../../../../components/ui/Badge';
import { SettingsCard } from '../../../../../../components/ui/SettingsCard';
import { PageSpinner } from '../../../../../../components/ui/Spinner';
import type { FolioImport } from '../../../../../../services/api/folioImports';
import * as S from './style';

const TONE = { created: 'accent', updated: 'warning', failed: 'danger' } as const;

/** Step 3: the run, while it goes and once it's done: what each page became. */
export function ImportOutcome({ item }: { item: FolioImport }) {
  const { t } = useTranslation();
  if (item.status === 'running') {
    return (
      <SettingsCard title={t('folio.imports.running')} help={t('folio.imports.runningHelp')}>
        <PageSpinner />
      </SettingsCard>
    );
  }
  if (item.status === 'failed') {
    return (
      <SettingsCard title={t('folio.imports.failed')}>
        <S.Problem role="alert">{item.stats.error}</S.Problem>
      </SettingsCard>
    );
  }
  const pages = item.report.run ?? [];
  return (
    <SettingsCard title={t('folio.imports.done')} help={t('folio.imports.doneHelp')}>
      <S.Summary>
        {(['created', 'updated', 'published', 'drafts', 'failed'] as const).map((k) => (
          <span key={k}>
            <strong>{item.stats[k] ?? 0}</strong> {t(`folio.imports.outcome.${k}`)}
          </span>
        ))}
      </S.Summary>
      <S.List>
        {pages.map((p) => (
          <li key={p.external_id}>
            <Badge tone={TONE[p.action]}>{t(`folio.imports.results.${p.action}`)}</Badge>
            {p.node_id ? (
              <Link to="/folio/p/$page" params={{ page: p.node_id }}>
                {p.title}
              </Link>
            ) : (
              <span>{p.title}</span>
            )}
            {p.published && <small>{t('folio.imports.published')}</small>}
            {p.missing && p.missing.length > 0 && (
              <small>{t('folio.imports.missing', { fields: p.missing.join(', ') })}</small>
            )}
            {p.errors.map((e) => (
              <S.PageError key={e}>{e}</S.PageError>
            ))}
          </li>
        ))}
      </S.List>
    </SettingsCard>
  );
}
