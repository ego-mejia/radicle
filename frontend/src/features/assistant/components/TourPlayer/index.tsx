import { useRouter, useRouterState } from '@tanstack/react-router';
import { X } from 'lucide-react';
import { useCallback, useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '../../../../components/ui/Button';
import { useMe } from '../../../../hooks/useMe';
import {
  findTarget,
  pageFor,
  projectInPath,
  radiLook,
  type TourStep,
  waitForTarget,
} from '../../lib/tour';
import * as S from './style';

type Props = { steps: TourStep[]; onDone: () => void };
type Box = { top: number; left: number; width: number; height: number };

const MOVE_MS = 750;

/** **bold** in step texts, as in the chat. */
function withBold(text: string): React.ReactNode[] {
  return text
    .split(/\*\*(.+?)\*\*/g)
    .map((part, i) => (i % 2 ? <strong key={i}>{part}</strong> : part));
}
const pause = (ms: number) => new Promise((r) => setTimeout(r, ms));

/** Plays a tour: navigates, moves the cursor to each part, highlights it and explains. */
export function TourPlayer({ steps, onDone }: Props) {
  const { t } = useTranslation();
  const router = useRouter();
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const me = useMe();
  const [index, setIndex] = useState(0);
  const [box, setBox] = useState<Box | null>(null);
  const [cursor, setCursor] = useState(() => ({
    x: window.innerWidth - 60,
    y: window.innerHeight - 60,
  }));
  const [pressing, setPressing] = useState(false);
  const [missing, setMissing] = useState(false);
  const target = useRef<HTMLElement | null>(null);
  const project = useRef(projectInPath(pathname) ?? me.projects[0]?.key ?? null);
  const step = steps[index];

  // Keep the highlight on the element while the page scrolls or resizes.
  useEffect(() => {
    let frame = 0;
    const follow = () => {
      const el = target.current;
      if (el?.isConnected) {
        const r = el.getBoundingClientRect();
        setBox((b) =>
          b && b.top === r.top && b.left === r.left && b.width === r.width && b.height === r.height
            ? b
            : { top: r.top, left: r.left, width: r.width, height: r.height },
        );
      }
      frame = requestAnimationFrame(follow);
    };
    frame = requestAnimationFrame(follow);
    return () => cancelAnimationFrame(frame);
  }, []);

  useEffect(() => {
    if (!step) return;
    let cancelled = false;
    void (async () => {
      setMissing(false);
      setBox(null);
      let el = findTarget(step.target);
      const page = pageFor(step, project.current);
      if (!el && page) {
        router.history.push(page);
        el = await waitForTarget(step.target);
      } else if (!el) {
        el = await waitForTarget(step.target, 1500);
      }
      if (cancelled) return;
      target.current = el;
      if (!el) {
        setMissing(true);
        return;
      }
      el.scrollIntoView({ block: 'center', behavior: 'smooth' });
      await pause(250);
      const r = el.getBoundingClientRect();
      const x = r.left + Math.min(r.width / 2, 40);
      const y = r.top + r.height / 2;
      setCursor({ x, y });
      radiLook(x, y);
      await pause(MOVE_MS);
      if (cancelled || step.action !== 'click') return;
      setPressing(true);
      await pause(160);
      setPressing(false);
      el.click();
      const after = projectInPath(window.location.pathname);
      if (after) project.current = after;
    })();
    return () => {
      cancelled = true;
    };
  }, [step, router]);

  const next = useCallback(() => {
    if (index + 1 >= steps.length) onDone();
    else setIndex(index + 1);
  }, [index, steps.length, onDone]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onDone();
      else if (e.key === 'ArrowRight') next();
      else if (e.key === 'ArrowLeft' && index > 0) setIndex(index - 1);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [index, next, onDone]);

  if (!step) return null;
  const below = !box || box.top + box.height + 180 < window.innerHeight;
  const card = box
    ? {
        top: below ? box.top + box.height + 14 : Math.max(12, box.top - 14),
        left: Math.min(Math.max(12, box.left), window.innerWidth - 340),
        transform: below ? undefined : 'translateY(-100%)',
      }
    : { bottom: 110, right: 24 };

  return (
    <S.Layer aria-live="polite">
      {box && (
        <S.Spotlight
          style={{
            top: box.top - 6,
            left: box.left - 6,
            width: box.width + 12,
            height: box.height + 12,
          }}
        />
      )}
      <S.CursorX style={{ transform: `translateX(${cursor.x}px)` }}>
        <S.CursorY style={{ transform: `translateY(${cursor.y}px)` }}>
          <S.Cursor $pressing={pressing} viewBox="0 0 24 28" aria-hidden="true">
            <path d="M3 2 L3 22 L8.5 17 L12.5 26 L16 24.4 L12 15.6 L19.5 15.6 Z" />
          </S.Cursor>
        </S.CursorY>
      </S.CursorX>
      <S.Card
        style={card}
        role="dialog"
        aria-label={t('assistant.tour.title')}
        // Dialogs close on clicks outside them; the tour card must not count as outside.
        onPointerDown={(e) => e.stopPropagation()}
        onFocusCapture={(e) => e.stopPropagation()}
      >
        <S.CardHead>
          <small>{t('assistant.tour.step', { n: index + 1, total: steps.length })}</small>
          <S.Stop type="button" aria-label={t('assistant.tour.stop')} onClick={onDone}>
            <X size={14} />
          </S.Stop>
        </S.CardHead>
        <p>{missing ? t('assistant.tour.missing') : withBold(step.text)}</p>
        <S.CardActions>
          {index > 0 && (
            <Button size="sm" variant="ghost" onClick={() => setIndex(index - 1)}>
              {t('assistant.tour.back')}
            </Button>
          )}
          <Button size="sm" variant="primary" onClick={next} autoFocus>
            {index + 1 >= steps.length ? t('assistant.tour.done') : t('assistant.tour.next')}
          </Button>
        </S.CardActions>
      </S.Card>
    </S.Layer>
  );
}
