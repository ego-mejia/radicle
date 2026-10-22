import { useQuery } from '@tanstack/react-query';
import { useParams } from '@tanstack/react-router';
import { useEffect, useState } from 'react';
import i18n from '../../../../i18n';
import { fetchPrint, printAssetUrl } from '../../../../services/api/folioPublic';
import { PublicArticle } from '../../components/PublicArticle';
import { printLanguage } from './language';
import * as S from './style';

/** Time for lazily loaded diagrams, formulas and charts to draw before printing. */
export const SETTLE_MS = 2500;

/** An export's pages one after another, a page break between them, for the worker's
 * browser to print to PDF. It marks itself `data-print-ready` once everything drew. */
export function FolioPrintView() {
  const { token } = useParams({ strict: false }) as { token: string };
  const print = useQuery({ queryKey: ['folio', 'print', token], queryFn: () => fetchPrint(token) });
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!print.data) return;
    const lang = printLanguage(print.data.pages[0]?.metadata);
    if (lang && lang !== i18n.language) void i18n.changeLanguage(lang);
    let done = false;
    const timer = window.setTimeout(async () => {
      await document.fonts?.ready;
      if (!done) setReady(true);
    }, SETTLE_MS);
    return () => {
      done = true;
      window.clearTimeout(timer);
    };
  }, [print.data]);

  if (print.isError) return <S.Failed data-print-ready>{String(print.error)}</S.Failed>;
  if (!print.data) return null;
  return (
    <S.Pages data-print-ready={ready ? '' : undefined}>
      <S.PrintBody />
      {print.data.pages.map((page) => (
        <S.Sheet key={page.id}>
          <PublicArticle page={page} env={{ assetUrl: (id) => printAssetUrl(token, id) }} />
        </S.Sheet>
      ))}
    </S.Pages>
  );
}
