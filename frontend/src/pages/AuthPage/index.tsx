import { Outlet } from '@tanstack/react-router';
import { useTranslation } from 'react-i18next';
import { Logo } from '../../components/icons/Logo';
import * as S from './style';

/** Centered card for setup and sign in, outside the app shell. */
export function AuthPage() {
  const { t } = useTranslation();
  return (
    <S.Page>
      <S.Card>
        <S.Brand>
          <Logo size={34} />
          {t('app.name')}
        </S.Brand>
        <Outlet />
      </S.Card>
    </S.Page>
  );
}
