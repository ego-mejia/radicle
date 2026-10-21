import { useEffect, useId, useMemo, useRef, useState } from 'react';
import { useTheme } from 'styled-components';
import { useReducedMotion } from '../../../../hooks/useReducedMotion';
import { themes, type ThemeMode } from '../../../../styles/theme';
import { visualTheme } from './tokens';
import {
  HEIGHT_MESSAGE,
  MAX_HEIGHT,
  THEME_MESSAGE,
  VISUAL_SANDBOX,
  visualDocument,
} from './visualDocument';
import * as S from './style';

type Props = {
  code: string;
  title?: string | null;
  description: string;
  /** Show it in this mode instead of the page's (the Visual editor's preview toggle). */
  mode?: ThemeMode;
};

/** A Visual block (Folio 3.3): SVG or HTML in a sandboxed iframe that follows the theme
 * without reloading and grows with its content, up to 2,000 px. */
export function VisualFrame({ code, title, description, mode }: Props) {
  const pageTheme = useTheme();
  const reducedMotion = useReducedMotion();
  const frame = useRef<HTMLIFrameElement>(null);
  const [height, setHeight] = useState(150);
  const describedBy = useId();
  const theme = visualTheme(mode ? themes[mode] : pageTheme, reducedMotion);
  const latest = useRef(theme);
  latest.current = theme;

  // The code decides the document; the theme travels by message, so a new theme doesn't
  // reload the visual.
  const srcDoc = useMemo(() => visualDocument(code, latest.current), [code]);

  const sendTheme = () =>
    frame.current?.contentWindow?.postMessage({ type: THEME_MESSAGE, ...latest.current }, '*');
  const themeKey = JSON.stringify(theme);
  useEffect(sendTheme, [themeKey]);

  useEffect(() => {
    const onMessage = (e: MessageEvent) => {
      if (e.source !== frame.current?.contentWindow || e.data?.type !== HEIGHT_MESSAGE) return;
      const next = Number(e.data.height);
      if (Number.isFinite(next)) setHeight(Math.min(Math.max(Math.ceil(next), 1), MAX_HEIGHT));
    };
    window.addEventListener('message', onMessage);
    return () => window.removeEventListener('message', onMessage);
  }, []);

  return (
    <S.Figure>
      <S.Frame
        ref={frame}
        title={title || description}
        aria-describedby={describedBy}
        sandbox={VISUAL_SANDBOX}
        srcDoc={srcDoc}
        referrerPolicy="no-referrer"
        onLoad={sendTheme}
        style={{ height }}
      />
      {title ? <S.Caption>{title}</S.Caption> : null}
      <S.Description id={describedBy}>{description}</S.Description>
    </S.Figure>
  );
}
