// Lime palette tokens from the control document. Components read them through
// styled-components: `${({ theme }) => theme.color.accent}`.

const fonts = {
  ui: "'Inter', system-ui, -apple-system, 'Segoe UI', sans-serif",
  mono: "'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, monospace",
};

const space = { xs: '4px', sm: '8px', md: '12px', lg: '16px', xl: '24px', xxl: '32px' };
const radius = { sm: '4px', md: '6px', lg: '10px', full: '999px' };
const fontSize = { xs: '11px', sm: '12px', md: '13px', lg: '15px', xl: '18px', xxl: '24px' };

export type ThemeMode = 'light' | 'dark';

type Palette = Record<
  | 'bg'
  | 'surface'
  | 'surface2'
  | 'border'
  | 'text'
  | 'textMuted'
  | 'accent'
  | 'accentFill'
  | 'onAccent'
  | 'accentSoft'
  | 'danger'
  | 'warning'
  | 'catTodo'
  | 'catProgress'
  | 'catDone',
  string
>;

export type Theme = {
  mode: ThemeMode;
  color: Palette;
  fonts: typeof fonts;
  space: typeof space;
  radius: typeof radius;
  fontSize: typeof fontSize;
};

export const lightTheme: Theme = {
  mode: 'light',
  color: {
    bg: '#F5F6F8',
    surface: '#FFFFFF',
    surface2: '#F1F2F4',
    border: '#E5E7EB',
    text: '#111827',
    textMuted: '#6B7280',
    accent: '#4D7C0F',
    accentFill: '#C6F432',
    onAccent: '#1A2E05',
    accentSoft: '#ECF8C8',
    danger: '#DC2626',
    warning: '#B45309',
    // Status categories in charts: grey to do, lime in progress, dark green done.
    catTodo: '#9CA3AF',
    catProgress: '#C6F432',
    catDone: '#4D7C0F',
  },
  fonts,
  space,
  radius,
  fontSize,
};

export const darkTheme: Theme = {
  ...lightTheme,
  mode: 'dark',
  color: {
    bg: '#0E0F11',
    surface: '#17191C',
    surface2: '#23262A',
    border: '#2A2D31',
    text: '#E6E6E6',
    textMuted: '#7C8591',
    accent: '#C6F432',
    accentFill: '#C6F432',
    onAccent: '#1A2E05',
    accentSoft: '#2A3311',
    danger: '#F87171',
    warning: '#F5A524',
    catTodo: '#4B5563',
    catProgress: '#C6F432',
    catDone: '#65A30D',
  },
};

export const themes: Record<ThemeMode, Theme> = { light: lightTheme, dark: darkTheme };
