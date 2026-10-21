import * as Dropdown from '@radix-ui/react-dropdown-menu';
import { useNavigate } from '@tanstack/react-router';
import { BookOpen, Check, ChevronDown, KanbanSquare, Settings } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useMe } from '../../../hooks/useMe';
import { useSuiteApps } from '../../../hooks/useSuiteApps';
import { type SuiteApp, lastRoute } from '../../../lib/suite';
import { Logo } from '../../icons/Logo';
import * as S from './style';

const ICONS: Record<SuiteApp, React.ReactNode> = {
  docket: <KanbanSquare aria-hidden />,
  folio: <BookOpen aria-hidden />,
};
const KEYS: Record<SuiteApp, string> = { docket: 'G D', folio: 'G F' };

/** The logo as a switch between the suite's apps (Folio 0.4). Each app opens where the
 * user left it; only the apps they can open are listed. */
export function SuiteSwitch({ current }: { current: SuiteApp }) {
  const { t } = useTranslation();
  const me = useMe();
  const apps = useSuiteApps();
  const navigate = useNavigate();
  const go = (href: string) => void navigate({ to: href });

  return (
    <Dropdown.Root>
      <Dropdown.Trigger asChild>
        <S.Trigger
          type="button"
          aria-label={t('suite.switch', { app: t(`suite.apps.${current}.name`) })}
        >
          <Logo size={26} />
          {t('app.name')}
          <S.Badge>{t(`suite.apps.${current}.badge`)}</S.Badge>
          <ChevronDown aria-hidden />
        </S.Trigger>
      </Dropdown.Trigger>
      <Dropdown.Portal>
        <S.Content align="start" sideOffset={8} aria-label={t('suite.menu')}>
          <S.Label>{t('suite.switchTo')}</S.Label>
          {apps.map((app) => (
            <S.App
              key={app}
              $current={app === current}
              aria-current={app === current ? 'true' : undefined}
              onSelect={() => app !== current && go(lastRoute(app, me.handle))}
            >
              <S.Tile $app={app}>{ICONS[app]}</S.Tile>
              <S.Text>
                <b>{t(`suite.apps.${app}.name`)}</b>
                <small>{t(`suite.apps.${app}.description`)}</small>
              </S.Text>
              {app === current ? (
                <S.Check>
                  <Check aria-label={t('suite.current')} />
                </S.Check>
              ) : (
                <S.Keys>{KEYS[app]}</S.Keys>
              )}
            </S.App>
          ))}
          {me.is_instance_admin && (
            <>
              <S.Separator />
              <S.Admin onSelect={() => go('/admin')}>
                <Settings aria-hidden />
                {t('suite.admin')}
              </S.Admin>
            </>
          )}
          <S.Note>{t('suite.note')}</S.Note>
        </S.Content>
      </Dropdown.Portal>
    </Dropdown.Root>
  );
}
