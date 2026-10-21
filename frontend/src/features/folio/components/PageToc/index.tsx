import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import type { Heading } from '../DocContent/anchors';
import * as S from './style';

/** The heading the reader is at: the last one whose top crossed the upper third. */
function useCurrentSection(anchors: string[]): string | undefined {
  const [current, setCurrent] = useState<string | undefined>(anchors[0]);
  // Anchors have no spaces, so the joined string is a stable dependency.
  const key = anchors.join(' ');
  useEffect(() => {
    const list = key ? key.split(' ') : [];
    if (typeof IntersectionObserver === 'undefined') return;
    const visible = new Set<string>();
    const observer = new IntersectionObserver(
      (entries) => {
        for (const e of entries) {
          if (e.isIntersecting) visible.add(e.target.id);
          else visible.delete(e.target.id);
        }
        const first = list.find((a) => visible.has(a));
        if (first) setCurrent(first);
      },
      { rootMargin: '0px 0px -66% 0px' },
    );
    for (const anchor of list) {
      const el = document.getElementById(anchor);
      if (el) observer.observe(el);
    }
    return () => observer.disconnect();
  }, [key]);
  return current;
}

/** "On this page": the page's sections, with the one being read highlighted. */
export function PageToc({ headings }: { headings: Heading[] }) {
  const { t } = useTranslation();
  const current = useCurrentSection(headings.map((h) => h.anchor));
  if (!headings.length) return null;
  return (
    <S.Toc aria-label={t('folio.reader.toc')}>
      <S.Title>{t('folio.reader.toc')}</S.Title>
      {headings.map((h) => (
        <S.Item
          key={h.anchor}
          href={`#${h.anchor}`}
          $depth={Math.max(0, h.level - 1)}
          aria-current={h.anchor === current ? 'location' : undefined}
        >
          {h.text}
        </S.Item>
      ))}
    </S.Toc>
  );
}
