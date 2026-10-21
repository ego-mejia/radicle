import { useQuery } from '@tanstack/react-query';
import { FileText, FolderTree } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { fetchTemplates, folioKeys, type FolioTemplate } from '../../../../services/api/folio';
import { DocContent } from '../DocContent';
import type { DocNode } from '../DocContent/anchors';
import * as S from './style';

type Props = {
  /** Page templates (the default) or space templates. */
  kind?: 'page' | 'space';
  space?: string;
  /** The chosen template's id, or null for a blank page or an empty space. */
  value: string | null;
  onChange: (id: string | null) => void;
};

type Item = { title?: unknown; kind?: unknown; children?: unknown };

/** A space template's folders and pages as a nested list. */
function Outline({ items }: { items: unknown }) {
  if (!Array.isArray(items) || items.length === 0) return null;
  return (
    <S.Outline>
      {(items as Item[]).map((item, i) => (
        <li key={i}>
          {item.kind === 'folder' ? '📁' : '📄'} {String(item.title ?? '')}
          <Outline items={item.children} />
        </li>
      ))}
    </S.Outline>
  );
}

/** A gallery of page or space templates with a preview of the chosen one; "Blank" comes
 * first. */
export function TemplatePicker({ kind = 'page', space, value, onChange }: Props) {
  const { t } = useTranslation();
  const { data: templates = [] } = useQuery({
    queryKey: folioKeys.templates(kind, space),
    queryFn: () => fetchTemplates(kind, space),
  });
  const blank = kind === 'page' ? 'blank' : 'blankSpace';
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
            {kind === 'page' ? <FileText size={18} /> : <FolderTree size={18} />}
          </S.Icon>
          <S.Name>{t(`folio.templates.${blank}`)}</S.Name>
          <S.Description>{t(`folio.templates.${blank}Hint`)}</S.Description>
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
            <S.Icon aria-hidden>{tpl.icon ?? (kind === 'page' ? '📄' : '🗂️')}</S.Icon>
            <S.Name>{tpl.name}</S.Name>
            <S.Description>{tpl.description}</S.Description>
          </S.Card>
        ))}
      </S.Grid>
      {kind === 'space' && chosen && (
        <S.Preview aria-label={t('folio.templates.preview', { name: chosen.name })}>
          <Outline items={chosen.structure?.pages} />
        </S.Preview>
      )}
      {kind === 'page' && chosen?.content_json && (
        <S.Preview aria-label={t('folio.templates.preview', { name: chosen.name })}>
          <DocContent doc={chosen.content_json as DocNode} />
        </S.Preview>
      )}
    </S.Wrap>
  );
}
