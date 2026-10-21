import { useQuery } from '@tanstack/react-query';
import { Link } from '@tanstack/react-router';
import { BookOpen } from 'lucide-react';
import { type RefObject, useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { useTranslation } from 'react-i18next';
import { aiKeys, fetchGlossary, type GlossaryTerm } from '../../../../services/api/folioAi';
import { glossaryMatches, type Match } from '../../hooks/glossaryMatch';
import * as S from './style';

const NAME = 'folio-glossary';

type Highlights = { set: (name: string, h: unknown) => void; delete: (name: string) => void };
type HighlightCtor = new (...ranges: Range[]) => unknown;
type Shown = { term: GlossaryTerm; top: number; left: number };

type Props = {
  container: RefObject<HTMLElement | null>;
  /** Changes when the content does, so the terms are found again. */
  version: unknown;
};

/** Approved glossary terms in the page (Folio 4.6): underlined without touching React's DOM
 * (CSS Custom Highlight API), with their definition and source when the pointer is on one. */
export function GlossaryTooltips({ container, version }: Props) {
  const { t } = useTranslation();
  const glossary = useQuery({
    queryKey: aiKeys.glossary('approved'),
    queryFn: () => fetchGlossary(),
    staleTime: 5 * 60_000,
    retry: false,
  });
  const matches = useRef<Match[]>([]);
  const [shown, setShown] = useState<Shown | null>(null);
  const hideTimer = useRef<number>(undefined);

  useEffect(() => {
    const root = container.current;
    const terms = glossary.data ?? [];
    if (!root || !terms.length) return;
    matches.current = glossaryMatches(root, terms);
    const css = (globalThis as { CSS?: { highlights?: Highlights } }).CSS;
    const Highlight = (globalThis as { Highlight?: HighlightCtor }).Highlight;
    if (css?.highlights && Highlight) {
      css.highlights.set(NAME, new Highlight(...matches.current.map((m) => m.range)));
    }
    const over = (e: MouseEvent) => {
      const hit = matches.current.find((m) =>
        Array.from(m.range.getClientRects()).some(
          (r) =>
            e.clientX >= r.left &&
            e.clientX <= r.right &&
            e.clientY >= r.top &&
            e.clientY <= r.bottom,
        ),
      );
      window.clearTimeout(hideTimer.current);
      if (hit) {
        const rect = hit.range.getBoundingClientRect();
        setShown((s) =>
          s?.term.id === hit.term.id
            ? s
            : { term: hit.term, top: rect.bottom + 6, left: rect.left },
        );
      } else {
        // A moment to reach the tooltip's link.
        hideTimer.current = window.setTimeout(() => setShown(null), 250);
      }
    };
    // Hover is a mouse thing; touch has no pointer to rest on a word.
    root.addEventListener('mousemove', over);
    return () => {
      root.removeEventListener('mousemove', over);
      window.clearTimeout(hideTimer.current);
      css?.highlights?.delete(NAME);
    };
  }, [container, glossary.data, version]);

  if (!shown) return null;
  const { term } = shown;
  return createPortal(
    <S.Tip
      role="tooltip"
      style={{ top: shown.top, left: shown.left }}
      onMouseEnter={() => window.clearTimeout(hideTimer.current)}
      onMouseLeave={() => setShown(null)}
    >
      <S.Term>
        <BookOpen aria-hidden />
        {term.term}
      </S.Term>
      <S.Definition>{term.definition}</S.Definition>
      {term.source && (
        <S.Source>
          <Link to="/folio/p/$page" params={{ page: `${term.source.id}-${term.source.slug}` }}>
            {t('folio.glossary.source', { title: term.source.title })}
          </Link>
        </S.Source>
      )}
    </S.Tip>,
    document.body,
  );
}
