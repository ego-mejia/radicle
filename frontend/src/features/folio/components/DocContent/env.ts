import { createContext, type ReactNode, useContext } from 'react';
import { assetUrl } from '../../../../services/api/folio';
import type { ChildPage } from './components/RichBlock';

/** Where a document is read. Inside Folio by default; a public link swaps the asset
 * URLs and child page links, and blocks that need an account show a note instead. */
export type DocEnv = {
  assetUrl: (assetId: string) => string;
  /** Read by a stranger through a public link. */
  isPublic: boolean;
  /** A child page's link; Folio's reader route when unset. */
  pageLink?: (page: ChildPage) => ReactNode;
};

export const DocEnvContext = createContext<DocEnv>({ assetUrl, isPublic: false });

export function useDocEnv(): DocEnv {
  return useContext(DocEnvContext);
}
