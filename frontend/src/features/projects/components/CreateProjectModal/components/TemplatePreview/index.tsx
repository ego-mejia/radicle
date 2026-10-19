import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { CategoryIcon } from '../../../../../../components/icons/CategoryIcon';
import { fetchTemplate, templateKeys } from '../../../../../../services/api/templates';
import { TICKET_TYPES } from '../../../../../../services/api/types';
import * as S from './style';

/** Statuses per type and custom fields of the template about to be used. */
export function TemplatePreview({ templateId }: { templateId: string }) {
  const { t } = useTranslation();
  const { data } = useQuery({
    queryKey: templateKeys.detail(templateId),
    queryFn: () => fetchTemplate(templateId),
  });
  if (!data) return <S.Box aria-busy="true" />;
  const fields = data.config.custom_fields ?? [];
  return (
    <S.Box aria-label={t('templates.preview')}>
      {TICKET_TYPES.map((type) => (
        <S.Line key={type}>
          <strong>{t(`ticket.types.${type}`)}</strong>
          {data.config.workflows[type]?.statuses.map((s) => (
            <S.Status key={s.ref}>
              <CategoryIcon category={s.category} size={12} />
              {s.name}
            </S.Status>
          ))}
        </S.Line>
      ))}
      {fields.length > 0 && (
        <S.Line>
          <strong>{t('settings.fields')}</strong>
          {fields.map((f) => f.name).join(', ')}
        </S.Line>
      )}
      {(data.config.areas ?? []).length > 0 && (
        <S.Line>
          <strong>{t('settings.areas')}</strong>
          {(data.config.areas ?? []).map((a) => a.name).join(', ')}
        </S.Line>
      )}
    </S.Box>
  );
}
