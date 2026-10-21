import { type ReactNode, type Ref, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { DocContent } from '../DocContent';
import { type DocNode, readingMinutes } from '../DocContent/anchors';
import type { ChildPage } from '../DocContent/components/RichBlock';
import * as S from './style';

type Props = {
  title: string;
  /** Small caps above the title, e.g. "how-to · Ingeniería". */
  kicker: string;
  description: string;
  content: DocNode | null | undefined;
  childPages: ChildPage[];
  onExit: () => void;
  /** Beside the column, e.g. the inline comments. */
  margin?: ReactNode;
  /** Wraps the page's content, for selection and highlights. */
  contentRef?: Ref<HTMLDivElement>;
};

/** How far down the page the reader is, from 0 to 1. */
function useScrollProgress(): number {
  const [progress, setProgress] = useState(0);
  useEffect(() => {
    const update = () => {
      const max = document.documentElement.scrollHeight - window.innerHeight;
      setProgress(max > 0 ? Math.min(1, Math.max(0, window.scrollY / max)) : 0);
    };
    update();
    window.addEventListener('scroll', update, { passive: true });
    window.addEventListener('resize', update);
    return () => {
      window.removeEventListener('scroll', update);
      window.removeEventListener('resize', update);
    };
  }, []);
  return progress;
}

/** Focus mode: one narrow column, larger type, a progress bar and the minutes left. */
export function FocusReader({
  title,
  kicker,
  description,
  content,
  childPages,
  onExit,
  margin,
  contentRef,
}: Props) {
  const { t } = useTranslation();
  const progress = useScrollProgress();
  const minutes = readingMinutes(content);
  const left = Math.max(0, Math.ceil(minutes * (1 - progress)));
  return (
    <S.Page>
      <S.Progress
        role="progressbar"
        aria-label={t('folio.reader.focus.progress')}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={Math.round(progress * 100)}
      >
        <S.Fill style={{ width: `${progress * 100}%` }} />
      </S.Progress>
      <S.Bar>
        <S.BarTitle>{title}</S.BarTitle>
        <S.Left>{t('folio.reader.focus.left', { count: left })}</S.Left>
        <S.Exit type="button" onClick={onExit}>
          {t('folio.reader.focus.exit')}
        </S.Exit>
      </S.Bar>
      <S.Body>
        <S.Column>
          {kicker && <S.Kicker>{kicker}</S.Kicker>}
          <S.Title>{title}</S.Title>
          {description && <S.Lead>{description}</S.Lead>}
          <div ref={contentRef}>
            <DocContent doc={content} childPages={childPages} size="large" />
          </div>
        </S.Column>
        {margin && <S.Side>{margin}</S.Side>}
      </S.Body>
    </S.Page>
  );
}
