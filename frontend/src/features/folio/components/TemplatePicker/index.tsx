import { useQuery } from '@tanstack/react-query';
import { FileText } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { fetchTemplates, folioKeys, type FolioTemplate } from '../../../../services/api/folio';
import { DocContent } from '../DocContent';
import type { DocNode } from '../DocContent/anchors';
import * as S from './style';

type Props = {
  space?: string;
  /** The chosen template's id, or null for a blank page. */
  value: string | null;
  onChange: (id: string | null) => void;
};

/** A gallery of page templates with a preview of the chosen one; "Blank" comes first. */
export function TemplatePicker({ space, value, onChange }: Props) {
  const { t } = useTranslation();
  const { data: templates = [] } = useQuery({
    queryKey: folioKeys.templates('page', space),
    queryFn: () => fetchTemplates('page', space),
  });
  const chosen: FolioTemplate | undefined = templates.find((tpl) => tpl.id === value);

  return (
    <S.Wrap>
      <S.Grid role="radiogroup" aria-label={t('folio.templates.choose')}>
        <S.Card
          type="button"
          role="radio"
          aria-checked={value === null}
          $active={value === null}
          onClick={() => onChange(null)}
        >
          <S.Icon aria-hidden>
            <FileText size={18} />
          </S.Icon>
          <S.Name>{t('folio.templates.blank')}</S.Name>
          <S.Description>{t('folio.templates.blankHint')}</S.Description>
        </S.Card>
        {templates.map((tpl) => (
          <S.Card
            key={tpl.id}
            type="button"
            role="radio"
            aria-checked={value === tpl.id}
            $active={value === tpl.id}
            onClick={() => onChange(tpl.id)}
          >
            <S.Icon aria-hidden>{tpl.icon ?? '📄'}</S.Icon>
            <S.Name>{tpl.name}</S.Name>
            <S.Description>{tpl.description}</S.Description>
          </S.Card>
        ))}
      </S.Grid>
      {chosen?.content_json && (
        <S.Preview aria-label={t('folio.templates.preview', { name: chosen.name })}>
          <DocContent doc={chosen.content_json as DocNode} />
        </S.Preview>
      )}
    </S.Wrap>
  );
}
