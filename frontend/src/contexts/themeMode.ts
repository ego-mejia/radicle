import { createContext } from 'react';
import type { ThemeMode } from '../styles/theme';

export type ThemePreference = ThemeMode | 'system';

export type ThemeModeValue = {
  preference: ThemePreference;
  mode: ThemeMode;
  setPreference: (preference: ThemePreference) => void;
};

export const ThemeModeContext = createContext<ThemeModeValue | null>(null);
