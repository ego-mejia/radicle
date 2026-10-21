import 'react-grid-layout/css/styles.css';
import { GripVertical, Trash2 } from 'lucide-react';
import GridLayout, { type Layout, WidthProvider } from 'react-grid-layout';
import { useTranslation } from 'react-i18next';
import { IconButton } from '../../../../../../components/ui/Button';
import type { HomeLayoutBlock } from '../../../../../../services/api/folio';
import { COLUMNS, MAX_HEIGHT, type Placement } from '../../state';
import * as S from './style';

const Grid = WidthProvider(GridLayout);
const ROW = 48;

type Props = {
  blocks: HomeLayoutBlock[];
  selected: string | null;
  invalid: Set<string>;
  onSelect: (id: string) => void;
  onPlace: (placements: Placement[]) => void;
  onRemove: (id: string) => void;
};

/** What a block shows, in a line: its source and how many. */
function summary(block: HomeLayoutBlock): string {
  const c = block.config as Record<string, unknown>;
  const parts = [c.space, c.label && `#${String(c.label)}`, c.rql, c.limit, c.markdown];
  return parts
    .filter((p) => p !== undefined && p !== null && p !== '')
    .map(String)
    .join(' · ')
    .slice(0, 80);
}

/** The 12-column canvas: blocks drag by their handle and resize from the corner. */
export function EditorGrid({ blocks, selected, invalid, onSelect, onPlace, onRemove }: Props) {
  const { t } = useTranslation();
  const layout: Layout[] = blocks.map((b) => ({
    i: b.id,
    x: b.x,
    y: b.y,
    w: b.w,
    h: b.h,
    minW: 2,
    maxH: MAX_HEIGHT,
  }));
  return (
    <S.Wrap>
      <Grid
        layout={layout}
        cols={COLUMNS}
        rowHeight={ROW}
        margin={[12, 12]}
        containerPadding={[0, 0]}
        draggableHandle=".home-block-drag"
        onDragStop={onPlace}
        onResizeStop={onPlace}
      >
        {blocks.map((block) => {
          const name = t(`folio.homeEditor.types.${block.type}`);
          const title = String((block.config as { title?: string }).title ?? '') || name;
          return (
            <S.Block
              key={block.id}
              $selected={block.id === selected}
              $invalid={invalid.has(block.id)}
              aria-label={title}
              onClick={() => onSelect(block.id)}
            >
              <S.Head>
                <S.Handle className="home-block-drag" aria-hidden>
                  <GripVertical />
                </S.Handle>
                <S.Type>{name}</S.Type>
                <IconButton
                  label={t('folio.homeEditor.remove', { title })}
                  onClick={(e) => {
                    e.stopPropagation();
                    onRemove(block.id);
                  }}
                >
                  <Trash2 />
                </IconButton>
              </S.Head>
              <S.Title>{title}</S.Title>
              <S.Summary>{summary(block)}</S.Summary>
            </S.Block>
          );
        })}
      </Grid>
    </S.Wrap>
  );
}
