/** Route params and hash of a hit's `url` (`/folio/p/<id>-<slug>#<anchor>`). */
export function hitTarget(url: string): { page: string; hash?: string } {
  const [path = '', hash] = url.split('#');
  return { page: path.replace(/^\/folio\/p\//, ''), hash: hash || undefined };
}
