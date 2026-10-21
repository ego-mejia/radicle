import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Modal } from '../../../../components/ui/Modal';
import { PageSpinner } from '../../../../components/ui/Spinner';
import { Tabs } from '../../../../components/ui/Tabs';
import { useErrorMessage } from '../../../../hooks/useErrorMessage';
import { formatDate } from '../../../../lib/format';
import { analyticsKeys, fetchPageAnalytics } from '../../../../services/api/folioAnalytics';
import { SummaryCards } from '../../../reports/components/ReportChart/components/SummaryCards';
import { ViewsChart } from '../ViewsChart';
import * as S from './style';

const RANGES = [7, 30, 90] as const;

type Props = { nodeId: string; open: boolean; onOpenChange: (open: boolean) => void };

/** A page's readership for its owner and space admins (Folio 5.9): views per day, unique
 * readers, reading time, and who read it when the space allows naming readers. */
export function PageAnalytics({ nodeId, open, onOpenChange }: Props) {
  const { t } = useTranslation();
  const errorMessage = useErrorMessage();
  const [days, setDays] = useState<(typeof RANGES)[number]>(30);
  const stats = useQuery({
    queryKey: analyticsKeys.page(nodeId, days),
    queryFn: () => fetchPageAnalytics(nodeId, days),
    enabled: open,
  });
  return (
    <Modal open={open} onOpenChange={onOpenChange} title={t('folio.analytics.title')} width={720}>
      <Tabs
        label={t('folio.analytics.range')}
        value={String(days)}
        onChange={(v) => setDays(Number(v) as (typeof RANGES)[number])}
        tabs={RANGES.map((r) => ({
          id: String(r),
          label: t('folio.analytics.days', { count: r }),
        }))}
      />
      {stats.isPending ? (
        <PageSpinner />
      ) : stats.isError ? (
        <S.Muted role="alert">{errorMessage(stats.error)}</S.Muted>
      ) : (
        <S.Body>
          <SummaryCards
            cards={[
              { label: t('folio.analytics.views'), value: stats.data.views, tone: 'accent' },
              { label: t('folio.analytics.uniqueReaders'), value: stats.data.unique_readers },
              {
                label: t('folio.analytics.readingTime'),
                value: t('folio.analytics.minutes', { count: stats.data.reading_minutes }),
              },
            ]}
          />
          <ViewsChart days={stats.data.daily} />
          <S.Heading>{t('folio.analytics.whoRead')}</S.Heading>
          {!stats.data.readers_visible ? (
            <S.Muted>{t('folio.analytics.readersHidden')}</S.Muted>
          ) : stats.data.readers.length === 0 ? (
            <S.Muted>{t('folio.analytics.noReaders')}</S.Muted>
          ) : (
            <S.Readers>
              {stats.data.readers.map((r) => (
                <li key={r.handle}>
                  <span>
                    {r.name} <small>@{r.handle}</small>
                  </span>
                  <small>
                    {t('folio.analytics.readerViews', { count: r.views })} ·{' '}
                    {formatDate(r.last_day)}
                  </small>
                </li>
              ))}
            </S.Readers>
          )}
        </S.Body>
      )}
    </Modal>
  );
}
