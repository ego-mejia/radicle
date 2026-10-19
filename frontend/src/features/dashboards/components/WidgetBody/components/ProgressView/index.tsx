import { useTranslation } from 'react-i18next';
import { formatDate } from '../../../../../../lib/format';
import * as S from './style';

type Summary = {
  milestone: string;
  percent_by_hours: number;
  percent_by_count: number;
  remaining_hours: number;
  forecast_date: string | null;
  target_date: string | null;
  state: string;
  reason: string;
};

/** Milestone progress: % by hours, hours left and the forecast against the target. */
export function ProgressView({ summary }: { summary: Summary }) {
  const { t } = useTranslation();
  const risk = summary.state === 'at_risk';
  return (
    <S.Wrap>
      <S.Big>{summary.percent_by_hours}%</S.Big>
      <S.Bar
        role="progressbar"
        aria-valuenow={summary.percent_by_hours}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={summary.milestone}
      >
        <span style={{ width: `${summary.percent_by_hours}%` }} />
      </S.Bar>
      <S.Line>
        {t('dashboards.progressLine', {
          count: summary.percent_by_count,
          hours: summary.remaining_hours,
        })}
      </S.Line>
      <S.State $risk={risk} title={summary.reason}>
        {t(`reports.states.${summary.state}`)}
        {summary.forecast_date &&
          ` · ${t('reports.forecast')} ${formatDate(summary.forecast_date)}`}
        {summary.target_date && ` · ${t('reports.target')} ${formatDate(summary.target_date)}`}
      </S.State>
    </S.Wrap>
  );
}
