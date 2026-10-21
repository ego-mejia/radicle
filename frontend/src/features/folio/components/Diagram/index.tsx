import { useEffect, useId, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useTheme } from 'styled-components';
import * as S from './style';

type Props = { source: string; caption?: string | null };

/** A Mermaid diagram (Folio 3.4) in Radicle's colors. Mermaid loads only when one shows,
 * and a diagram that doesn't compile says why instead of disappearing. */
export function Diagram({ source, caption }: Props) {
  const { t } = useTranslation();
  const theme = useTheme();
  const id = `dg${useId().replace(/[^a-zA-Z0-9]/g, '')}`;
  const [svg, setSvg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    void import('mermaid')
      .then(async ({ default: mermaid }) => {
        const c = theme.color;
        mermaid.initialize({
          startOnLoad: false,
          securityLevel: 'strict',
          theme: 'base',
          fontFamily: theme.fonts.ui,
          themeVariables: {
            darkMode: theme.mode === 'dark',
            background: c.surface,
            primaryColor: c.accentSoft,
            primaryBorderColor: c.accent,
            primaryTextColor: c.text,
            lineColor: c.textMuted,
            secondaryColor: c.surface2,
            tertiaryColor: c.surface,
            textColor: c.text,
          },
        });
        const { svg: drawn } = await mermaid.render(id, source);
        if (!cancelled) {
          setSvg(drawn);
          setError(null);
        }
      })
      .catch((e: unknown) => {
        if (!cancelled) setError(e instanceof Error ? e.message : String(e));
      });
    return () => {
      cancelled = true;
    };
  }, [source, id, theme]);

  return (
    <S.Figure>
      {error ? (
        <S.Error role="alert">
          <strong>{t('folio.reader.diagramError')}</strong>
          <span>{error.split('\n')[0]}</span>
          <pre>{source}</pre>
        </S.Error>
      ) : (
        <S.Drawing
          role="img"
          aria-label={caption || t('folio.reader.diagram')}
          aria-busy={!svg}
          // Mermaid's output with securityLevel strict: labels escaped, no scripts or links.
          dangerouslySetInnerHTML={svg ? { __html: svg } : undefined}
        />
      )}
      {caption ? <figcaption>{caption}</figcaption> : null}
    </S.Figure>
  );
}
