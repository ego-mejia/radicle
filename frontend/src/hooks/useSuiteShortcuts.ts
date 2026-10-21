import { useNavigate, useRouterState } from '@tanstack/react-router';
import { useContext, useEffect, useRef } from 'react';
import { ShortcutsContext } from '../contexts/shortcuts';
import { type SuiteApp, lastRoute, rememberRoute } from '../lib/suite';
import { typingIn } from './useHotkey';
import { useMe } from './useMe';
import { useSuiteApps } from './useSuiteApps';

const APP_KEYS: Record<string, SuiteApp> = { d: 'docket', f: 'folio' };

/** In either app: remember the page for the switch, and `g d` / `g f` to change apps. */
export function useSuiteShortcuts() {
  const me = useMe();
  const apps = useSuiteApps();
  const navigate = useNavigate();
  const enabled = useContext(ShortcutsContext);
  const href = useRouterState({ select: (s) => s.location.href });
  const pendingG = useRef(0);

  useEffect(() => rememberRoute(me.handle, href), [me.handle, href]);

  useEffect(() => {
    if (!enabled) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.metaKey || event.ctrlKey || event.altKey || typingIn(event.target)) return;
      if (document.querySelector('[role="dialog"]')) return;
      if (Date.now() - pendingG.current < 1200) {
        pendingG.current = 0;
        const app = APP_KEYS[event.key];
        if (app && apps.includes(app)) void navigate({ to: lastRoute(app, me.handle) });
        return;
      }
      if (event.key === 'g') pendingG.current = Date.now();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [enabled, apps, navigate, me.handle]);
}
