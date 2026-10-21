import { lazy } from 'react';

/** The canvas on its own chunk: Excalidraw only loads when a whiteboard is shown. */
export const LazyWhiteboardBoard = lazy(() =>
  import('.').then((m) => ({ default: m.WhiteboardBoard })),
);
