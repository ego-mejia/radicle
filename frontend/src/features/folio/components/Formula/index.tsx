import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import * as S from './style';

type Props = { latex: string; inline?: boolean };

/** A KaTeX formula (Folio 3.4), as a block or inside a line. KaTeX and its styles load
 * only when a formula shows; until then, and when it doesn't compile, the LaTeX shows. */
export function Formula({ latex, inline = false }: Props) {
  const { t } = useTranslation();
  const [html, setHtml] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    void Promise.all([import('katex'), import('katex/dist/katex.min.css')])
      .then(([{ default: katex }]) => {
        const out = katex.renderToString(latex, {
          displayMode: !inline,
          throwOnError: true,
          trust: false,
          output: 'htmlAndMathml',
        });
        if (!cancelled) {
          setHtml(out);
          setFailed(false);
        }
      })
      .catch(() => !cancelled && setFailed(true));
    return () => {
      cancelled = true;
    };
  }, [latex, inline]);

  const Box = inline ? S.Inline : S.Block;
  if (failed || !html)
    return (
      <Box
        as="code"
        title={failed ? t('folio.reader.formulaError') : undefined}
        data-failed={failed || undefined}
      >
        {latex}
      </Box>
    );
  // KaTeX's own markup, with trust off: no links, classes or styles from the formula.
  return <Box dangerouslySetInnerHTML={{ __html: html }} />;
}
