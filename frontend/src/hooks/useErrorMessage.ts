import { useTranslation } from 'react-i18next';
import { ApiError } from '../services/api/client';

/** API errors already carry an actionable English message; anything else gets a generic one. */
export function useErrorMessage(): (error: unknown) => string {
  const { t } = useTranslation();
  return (error) => (error instanceof ApiError ? error.message : t('common.unknownError'));
}
