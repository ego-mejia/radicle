import { LANGUAGES } from '../../../../i18n';

/** The language a PDF prints in: the first page's, so a Spanish doc reads "min de lectura"
 * whatever the worker's browser speaks. */
export function printLanguage(metadata: Record<string, unknown> | undefined): string | null {
  const lang = String(metadata?.language ?? '').slice(0, 2);
  return (LANGUAGES as readonly string[]).includes(lang) ? lang : null;
}
