import type { FolioHomeBlock } from '../../../../services/api/folio';
import { HomeBlock } from './components/HomeBlock';
import { inGridOrder } from './order';
import * as S from './style';

/** The home's 12-column grid as GET /home (or the editor's preview) resolves it. */
export function HomeGrid({ blocks }: { blocks: FolioHomeBlock[] }) {
  return (
    <S.Grid>
      {inGridOrder(blocks).map((block) => (
        <S.Cell
          key={block.id}
          data-block={block.type}
          $x={block.x}
          $y={block.y}
          $w={block.w}
          $h={block.h}
        >
          <HomeBlock block={block} />
        </S.Cell>
      ))}
    </S.Grid>
  );
}
