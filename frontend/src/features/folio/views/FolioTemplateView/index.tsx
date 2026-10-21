import { useQuery } from '@tanstack/react-query';
import { useParams } from '@tanstack/react-router';
import { useTranslation } from 'react-i18next';
import { EmptyState } from '../../../../components/ui/EmptyState';
import { PageSpinner } from '../../../../components/ui/Spinner';
import { fetchTemplate, folioKeys } from '../../../../services/api/folio';
import { TemplateForm } from '../../components/TemplateForm';

/** Folio → Admin → a template. */
export function FolioTemplateView() {
  const { t } = useTranslation();
  const { id } = useParams({ from: '/folio/folio/admin/templates/$id' });
  const { data, error } = useQuery({
    queryKey: folioKeys.template(id),
    queryFn: () => fetchTemplate(id),
  });
  if (error) return <EmptyState plant="seed" title={t('folio.templates.missing')} />;
  if (!data) return <PageSpinner />;
  return <TemplateForm key={data.id} template={data} />;
}
