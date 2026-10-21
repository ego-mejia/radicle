import { lazy, Suspense, useState } from 'react';
import { useTranslation } from 'react-i18next';
import type { ChartKind } from './components/ChartView';
import type { ChartData } from './tableData';
import * as S from './style';

const ChartView = lazy(() => import('./components/ChartView'));

type Props = { kind: ChartKind; title?: string | null; data: ChartData | null };

/** A chart block (Folio 3.4): bars, lines, area or pie from a table of numbers, with a
 * switch to read the same numbers as a table. */
export function ChartBlock({ kind, title, data }: Props) {
  const { t } = useTranslation();
  const [asTable, setAsTable] = useState(false);
  if (!data || data.length < 2) return <S.Empty>{t('folio.reader.chartEmpty')}</S.Empty>;

  const table = (
    <S.Table>
      <thead>
        <tr>
          {(data[0] ?? []).map((h, i) => (
            <th key={i}>{h}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {data.slice(1).map((row, r) => (
          <tr key={r}>
            {row.map((cell, i) => (
              <td key={i}>{cell}</td>
            ))}
          </tr>
        ))}
      </tbody>
    </S.Table>
  );

  return (
    <S.Figure>
      <S.Head>
        {title ? <figcaption>{title}</figcaption> : <span />}
        <S.Toggle type="button" aria-pressed={asTable} onClick={() => setAsTable(!asTable)}>
          {asTable ? t('folio.reader.showChart') : t('folio.reader.showTable')}
        </S.Toggle>
      </S.Head>
      {asTable ? (
        table
      ) : (
        <div role="img" aria-label={title || t('folio.reader.chart')}>
          <Suspense fallback={table}>
            <ChartView kind={kind} data={data} />
          </Suspense>
        </div>
      )}
    </S.Figure>
  );
}
