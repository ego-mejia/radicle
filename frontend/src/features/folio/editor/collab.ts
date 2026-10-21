// A shared document in the editor (Folio 2.2): the Y.Doc instead of TipTap's own state,
// and others' carets and selections in their colors.

import type { AnyExtension } from '@tiptap/core';
import Collaboration from '@tiptap/extension-collaboration';
import CollaborationCaret from '@tiptap/extension-collaboration-caret';
import type { Collab, Me } from '../hooks/useCollab';

export function collabExtensions(collab: Collab, me: Me): AnyExtension[] {
  return [
    // y-prosemirror's fragment, the one the server reads and writes.
    Collaboration.configure({ document: collab.doc, field: 'default' }),
    CollaborationCaret.configure({ provider: collab.provider, user: me }),
  ];
}
