import { useQuery } from '@tanstack/react-query';
import { Link } from '@tanstack/react-router';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { SettingsCard } from '../../../../components/ui/SettingsCard';
import { PageSpinner } from '../../../../components/ui/Spinner';
import { Tabs } from '../../../../components/ui/Tabs';
import { useErrorMessage } from '../../../../hooks/useErrorMessage';
import { formatDateTime } from '../../../../lib/format';
import { analyticsKeys, fetchSiteAnalytics } from '../../../../services/api/folioAnalytics';
import { SummaryCards } from '../../../reports/components/ReportChart/components/SummaryCards';
import { ViewsChart } from '../ViewsChart';
import * as S from './style';

const RANGES = ['7', '30', '90'] as const;

/** Folio, Admin, Analytics (Folio 5.9): activity, the most read content, and what people
 * search or ask without finding it, to know what to document next. */
export function SiteAnalytics() {
  const { t } = useTranslation();
  const errorMessage = useErrorMessage();
  const [range, setRange] = useState<(typeof RANGES)[number]>('30');
  const days = Number(range);
  const site = useQuery({
    queryKey: analyticsKeys.site(days),
    queryFn: () => fetchSiteAnalytics(days),
  });
  const s = site.data;
  return (
    <S.Wrap>
      <Tabs
        label={t('folio.analytics.range')}
        value={range}
        onChange={setRange}
        tabs={RANGES.map((r) => ({ id: r, label: t('folio.analytics.days', { count: +r }) }))}
      />
      {site.isPending ? (
        <PageSpinner />
      ) : site.isError || !s ? (
        <S.Muted role="alert">{errorMessage(site.error)}</S.Muted>
      ) : (
        <>
          <SummaryCards
            cards={[
              { label: t('folio.analytics.views'), value: s.views, tone: 'accent' },
              { label: t('folio.analytics.site.active'), value: s.active_users },
              { label: t('folio.analytics.site.searches'), value: s.searches },
              {
                label: t('folio.analytics.site.notFound'),
                value: s.no_results.reduce((n, g) => n + g.times, 0),
                tone: s.no_results.length ? 'warning' : undefined,
              },
            ]}
          />
          <SettingsCard title={t('folio.analytics.site.activity')}>
            <ViewsChart days={s.daily} />
          </SettingsCard>
          <S.Columns>
            <SettingsCard title={t('folio.analytics.site.topPages')}>
              {s.top_pages.length === 0 ? (
                <S.Muted>{t('folio.analytics.site.noViews')}</S.Muted>
              ) : (
                <S.Ranked>
                  {s.top_pages.map((p) => (
                    <li key={p.node_id}>
                      <Link to="/folio/p/$page" params={{ page: p.node_id }}>
                        {p.title}
                      </Link>
                      <small>
                        {p.space} · {t('folio.analytics.site.viewsReaders', p)}
                      </small>
                    </li>
                  ))}
                </S.Ranked>
              )}
            </SettingsCard>
            <SettingsCard title={t('folio.analytics.site.topSpaces')}>
              {s.top_spaces.length === 0 ? (
                <S.Muted>{t('folio.analytics.site.noViews')}</S.Muted>
              ) : (
                <S.Ranked>
                  {s.top_spaces.map((a) => (
                    <li key={a.key}>
                      <Link to="/folio/s/$key" params={{ key: a.key }}>
                        {a.name}
                      </Link>
                      <small>{t('folio.analytics.site.viewsReaders', a)}</small>
                    </li>
                  ))}
                </S.Ranked>
              )}
            </SettingsCard>
          </S.Columns>
          <S.Columns>
            <SettingsCard
              title={t('folio.analytics.site.gaps')}
              help={t('folio.analytics.site.gapsHelp')}
            >
              {s.no_results.length === 0 ? (
                <S.Muted>{t('folio.analytics.site.noGaps')}</S.Muted>
              ) : (
                <S.Ranked>
                  {s.no_results.map((g) => (
                    <li key={g.query}>
                      <S.Query>{g.query}</S.Query>
                      <small>
                        {t('folio.analytics.site.times', { count: g.times })} ·{' '}
                        {formatDateTime(g.last_at)}
                      </small>
                    </li>
                  ))}
                </S.Ranked>
              )}
            </SettingsCard>
            <SettingsCard title={t('folio.analytics.site.unanswered')}>
              {s.unanswered.length === 0 ? (
                <S.Muted>{t('folio.chat.unanswered.empty')}</S.Muted>
              ) : (
                <S.Ranked>
                  {s.unanswered.slice(0, 10).map((u, i) => (
                    <li key={i}>
                      <S.Query>{u.question}</S.Query>
                      <small>{formatDateTime(u.asked_at)}</small>
                    </li>
                  ))}
                </S.Ranked>
              )}
            </SettingsCard>
          </S.Columns>
        </>
      )}
    </S.Wrap>
  );
}
