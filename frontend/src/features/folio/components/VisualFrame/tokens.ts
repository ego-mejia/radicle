import type { Theme } from '../../../../styles/theme';
import type { VisualTheme } from './visualDocument';

/** The `--rdc-*` variables a visual sees, from the theme (the names agents read in
 * folio://guide/visuals; backend/radicle/folio/services/visuals.py lists them). */
export function visualTheme(theme: Theme, reducedMotion: boolean): VisualTheme {
  const c = theme.color;
  return {
    mode: theme.mode,
    reducedMotion,
    tokens: {
      '--rdc-bg': c.bg,
      '--rdc-surface': c.surface,
      '--rdc-text': c.text,
      '--rdc-muted': c.textMuted,
      '--rdc-accent': c.accent,
      '--rdc-accent-fill': c.accentFill,
      '--rdc-on-accent': c.onAccent,
      '--rdc-border': c.border,
      '--rdc-danger': c.danger,
      '--rdc-warning': c.warning,
      '--rdc-info': c.info,
      '--rdc-font': theme.fonts.ui,
      '--rdc-mono': theme.fonts.mono,
      '--rdc-radius': theme.radius.md,
    },
  };
}
