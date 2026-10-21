import { forwardRef, useEffect, useImperativeHandle, useState } from 'react';
import { useTranslation } from 'react-i18next';
import type { BlockItem } from '../../editor/blocks';
import * as S from './style';

export type SlashMenuHandle = { onKeyDown: (event: KeyboardEvent) => boolean };

type Props = { items: BlockItem[]; command: (item: BlockItem) => void };

/** The `/` menu: the blocks that match what you typed, picked with the arrows and Enter. */
export const SlashMenu = forwardRef<SlashMenuHandle, Props>(function SlashMenu(
  { items, command },
  ref,
) {
  const { t } = useTranslation();
  const [active, setActive] = useState(0);
  useEffect(() => setActive(0), [items]);

  useImperativeHandle(ref, () => ({
    onKeyDown: (event) => {
      if (!items.length) return false;
      if (event.key === 'ArrowDown') {
        setActive((i) => (i + 1) % items.length);
        return true;
      }
      if (event.key === 'ArrowUp') {
        setActive((i) => (i - 1 + items.length) % items.length);
        return true;
      }
      if (event.key === 'Enter') {
        const item = items[active];
        if (item) command(item);
        return true;
      }
      return false;
    },
  }));

  if (!items.length) {
    return (
      <S.Menu>
        <S.Empty>{t('folio.editor.noBlocks')}</S.Empty>
      </S.Menu>
    );
  }
  return (
    <S.Menu role="listbox" aria-label={t('folio.editor.blocksLabel')}>
      {items.map((item, i) => (
        <S.Item
          key={item.key}
          role="option"
          aria-selected={i === active}
          $active={i === active}
          onMouseEnter={() => setActive(i)}
          onMouseDown={(e) => e.preventDefault()}
          onClick={() => command(item)}
        >
          {t(`folio.editor.blocks.${item.key}`)}
        </S.Item>
      ))}
    </S.Menu>
  );
});
