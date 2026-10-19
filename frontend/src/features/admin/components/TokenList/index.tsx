import { useTranslation } from 'react-i18next';
import { Badge } from '../../../../components/ui/Badge';
import { Button } from '../../../../components/ui/Button';
import { relativeTime } from '../../../../lib/format';
import type { Token } from '../../../../services/api/types';
import { SettingsParts as S } from '../../../../components/ui/SettingsCard';

type Props = { tokens: Token[]; onRevoke: (id: string) => void };

export function TokenList({ tokens, onRevoke }: Props) {
  const { t } = useTranslation();
  if (tokens.length === 0) return <p>{t('admin.noTokens')}</p>;
  return (
    <S.Rows>
      {tokens.map((token) => (
        <S.Row key={token.id}>
          <S.Grow>
            <code>{token.prefix}…</code>
            {token.name}
            <small>
              {token.last_used_at
                ? t('admin.lastUsed', { when: relativeTime(token.last_used_at) })
                : t('admin.neverUsed')}
            </small>
          </S.Grow>
          {token.revoked_at ? (
            <Badge tone="danger">{t('admin.revoked')}</Badge>
          ) : (
            <Button size="sm" variant="danger" onClick={() => onRevoke(token.id)}>
              {t('admin.revoke')}
            </Button>
          )}
        </S.Row>
      ))}
    </S.Rows>
  );
}
