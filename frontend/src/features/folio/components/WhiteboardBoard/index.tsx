// The Excalidraw canvas of a whiteboard (Folio 3.5). Heavy: it loads on its own chunk
// (see ./lazy). Editors draw in the room, readers see the scene as it was last saved.

import '@excalidraw/excalidraw/index.css';
import { CaptureUpdateAction, Excalidraw, exportToBlob, exportToSvg } from '@excalidraw/excalidraw';
import type { BinaryFiles, ExcalidrawImperativeAPI } from '@excalidraw/excalidraw/types';
import { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useTheme } from 'styled-components';
import { POINTER_EVERY_MS } from '../../editor/presence';
import type { Collab } from '../../hooks/useCollab';
import { collaborators } from '../../whiteboard/collaborators';
import { elementsOf, merge, pushLocal, type SceneElement } from '../../whiteboard/sync';
import * as S from './style';

declare global {
  interface Window {
    EXCALIDRAW_ASSET_PATH?: string | string[];
  }
}
// Fonts come from Radicle's own build (vite.config.ts), not from a CDN.
if (import.meta.env.PROD) window.EXCALIDRAW_ASSET_PATH = '/assets/excalidraw/';

type Elements = Parameters<ExcalidrawImperativeAPI['updateScene']>[0]['elements'];

export type BoardExport = { png: () => Promise<Blob>; svg: () => Promise<Blob> };

type Props = {
  /** The scene to start from; for readers, the scene to show. */
  elements: SceneElement[];
  /** The room, for those who draw. */
  collab?: Collab;
  onExport?: (exporter: BoardExport) => void;
};

export function WhiteboardBoard({ elements, collab, onExport }: Props) {
  const { t, i18n } = useTranslation();
  const theme = useTheme();
  const [api, setApi] = useState<ExcalidrawImperativeAPI | null>(null);
  const lastPointer = useRef(0);
  const editable = !!collab;
  const doc = collab?.doc;
  const peers = collab?.peers;
  const [initial] = useState(() =>
    collab ? merge([], elementsOf(collab.doc).values()) : elements,
  );

  // Readers: the scene follows what the server returns.
  useEffect(() => {
    if (api && !editable)
      api.updateScene({
        elements: elements as unknown as Elements,
        captureUpdate: CaptureUpdateAction.NEVER,
      });
  }, [api, editable, elements]);

  // Editors: what others draw comes in from the room.
  useEffect(() => {
    if (!api || !doc) return;
    const map = elementsOf(doc);
    const onRemote = (_: unknown, tx: { origin: unknown }) => {
      if (tx.origin === 'local') return;
      const local = api.getSceneElementsIncludingDeleted() as unknown as SceneElement[];
      api.updateScene({
        elements: merge(local, map.values()) as unknown as Elements,
        captureUpdate: CaptureUpdateAction.NEVER,
      });
    };
    map.observe(onRemote);
    return () => map.unobserve(onRemote);
  }, [api, doc]);

  useEffect(() => {
    if (api && peers) api.updateScene({ collaborators: collaborators(peers) });
  }, [api, peers]);

  useEffect(() => {
    if (!api || !onExport) return;
    const scene = () => ({
      elements: api.getSceneElements(),
      appState: { ...api.getAppState(), exportBackground: true },
      files: api.getFiles() as BinaryFiles,
    });
    onExport({
      png: () => exportToBlob({ ...scene(), mimeType: 'image/png' }),
      svg: async () => {
        const svg = await exportToSvg(scene());
        return new Blob([svg.outerHTML], { type: 'image/svg+xml' });
      },
    });
  }, [api, onExport]);

  return (
    <S.Canvas aria-label={t('folio.whiteboard.canvas')}>
      <Excalidraw
        excalidrawAPI={setApi}
        initialData={{ elements: initial as unknown as Elements, scrollToContent: true }}
        viewModeEnabled={!editable}
        isCollaborating={editable}
        theme={theme.mode === 'dark' ? 'dark' : 'light'}
        langCode={i18n.language.startsWith('es') ? 'es-ES' : 'en'}
        UIOptions={{
          tools: { image: false },
          canvasActions: { loadScene: false, saveToActiveFile: false, export: false },
        }}
        onChange={(next) => {
          if (doc) pushLocal(doc, next as unknown as SceneElement[]);
        }}
        onPointerUpdate={({ pointer }) => {
          if (!collab) return;
          const now = Date.now();
          if (now - lastPointer.current < POINTER_EVERY_MS) return;
          lastPointer.current = now;
          collab.provider.awareness.setLocalStateField('pointer', {
            x: pointer.x,
            y: pointer.y,
            at: now,
          });
        }}
      />
    </S.Canvas>
  );
}
