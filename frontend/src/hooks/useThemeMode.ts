import { useContext } from 'react';
import { ThemeModeContext, type ThemeModeValue } from '../contexts/themeMode';

export function useThemeMode(): ThemeModeValue {
  const value = useContext(ThemeModeContext);
  if (!value) throw new Error('useThemeMode must be used inside ThemeModeProvider');
  return value;
}
