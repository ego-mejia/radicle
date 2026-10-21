import { useQuery } from '@tanstack/react-query';
import { NodeViewWrapper, type NodeViewProps } from '@tiptap/react';
import { Shapes } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Button } from '../../../../components/ui/Button';
import { Select } from '../../../../components/ui/Input';
import { folioKeys, queryDocs } from '../../../../services/api/folio';
import { WhiteboardEmbed } from '../WhiteboardEmbed';
import * as S from './style';

const WHITEBOARDS = 'kind = whiteboard ORDER BY title ASC';

/** The whiteboard block in the editor: which whiteboard it shows, and that whiteboard as
 * the page's readers will see it. */
export function WhiteboardBlock({ node, updateAttributes, selected }: NodeViewProps) {
  const { t } = useTranslation();
  const whiteboard = node.attrs.whiteboard as string | null;
  const options = useQuery({
    queryKey: folioKeys.query(WHITEBOARDS),
    queryFn: () => queryDocs(WHITEBOARDS, 100),
    enabled: !whiteboard || selected,
  });

  return (
    <NodeViewWrapper data-folio="whiteboard" contentEditable={false}>
      {(!whiteboard || selected) && (
        <S.Picker>
          <Shapes aria-hidden />
          <Select
            aria-label={t('folio.whiteboard.block.choose')}
            value={whiteboard ?? ''}
            onChange={(e) => updateAttributes({ whiteboard: e.target.value || null })}
          >
            <option value="">{t('folio.whiteboard.block.choose')}</option>
            {options.data?.items.map((w) => (
              <option key={w.id} value={w.id}>
                {w.title}
              </option>
            ))}
          </Select>
          {options.data?.items.length === 0 && <span>{t('folio.whiteboard.block.none')}</span>}
          {whiteboard && (
            <Button
              size="sm"
              variant="ghost"
              onClick={() => updateAttributes({ whiteboard: null })}
            >
              {t('common.remove')}
            </Button>
          )}
        </S.Picker>
      )}
      {whiteboard && <WhiteboardEmbed key={whiteboard} nodeId={whiteboard} />}
    </NodeViewWrapper>
  );
}
