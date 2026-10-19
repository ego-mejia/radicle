import { useTranslation } from 'react-i18next';
import type { ReportData } from '../../../../services/api/types';
import * as S from './style';

function show(value: unknown): string {
  if (value === null || value === undefined) return '—';
  if (typeof value === 'boolean') return value ? '✓' : '';
  if (typeof value === 'object') return JSON.stringify(value);
  return String(value);
}

/** The rows behind the chart, folded by default. */
export function DataTable({ report }: { report: ReportData }) {
  const { t } = useTranslation();
  return (
    <S.Details>
      <summary>{t('reports.data', { count: report.rows.length })}</summary>
      <S.Scroll>
        <table>
          <thead>
            <tr>
              {report.columns.map((c) => (
                <th key={c} scope="col">
                  {t(`reports.cols.${c}`, c)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {report.rows.map((row, i) => (
              <tr key={i}>
                {report.columns.map((c) => (
                  <td key={c}>{show(row[c])}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </S.Scroll>
    </S.Details>
  );
}
