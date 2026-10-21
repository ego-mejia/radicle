// The `/` menu: typing a slash opens SlashMenu at the cursor; picking a block replaces
// the slash and what follows it with that block.

import { Extension } from '@tiptap/core';
import { ReactRenderer } from '@tiptap/react';
import Suggestion, { type SuggestionOptions } from '@tiptap/suggestion';
import i18n from '../../../i18n';
import { SlashMenu, type SlashMenuHandle } from '../components/SlashMenu';
import { BLOCKS, findBlocks, type BlockItem } from './blocks';

type Options = { items: BlockItem[] };

function place(element: HTMLElement, rect: DOMRect | null | undefined) {
  if (!rect) return;
  element.style.position = 'fixed';
  element.style.zIndex = '40';
  element.style.left = `${rect.left}px`;
  element.style.top = `${rect.bottom + 6}px`;
}

const render: SuggestionOptions<BlockItem>['render'] = () => {
  let menu: ReactRenderer<SlashMenuHandle> | null = null;
  return {
    onStart: (props) => {
      menu = new ReactRenderer(SlashMenu, { props, editor: props.editor });
      document.body.appendChild(menu.element);
      place(menu.element as HTMLElement, props.clientRect?.());
    },
    onUpdate: (props) => {
      menu?.updateProps(props);
      if (menu) place(menu.element as HTMLElement, props.clientRect?.());
    },
    onKeyDown: ({ event }) => {
      if (event.key === 'Escape') {
        menu?.destroy();
        menu?.element.remove();
        menu = null;
        return true;
      }
      return menu?.ref?.onKeyDown(event) ?? false;
    },
    onExit: () => {
      menu?.element.remove();
      menu?.destroy();
      menu = null;
    },
  };
};

export const SlashCommand = Extension.create<Options>({
  name: 'slashCommand',
  addOptions: () => ({ items: BLOCKS }),
  addProseMirrorPlugins() {
    return [
      Suggestion<BlockItem>({
        editor: this.editor,
        char: '/',
        allowSpaces: true,
        items: ({ query }) =>
          findBlocks(this.options.items, query, (key) => i18n.t(`folio.editor.blocks.${key}`)),
        command: ({ editor, range, props }) => {
          props.run(editor.chain().focus().deleteRange(range)).run();
        },
        render,
      }),
    ];
  },
});
