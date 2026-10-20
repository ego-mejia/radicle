import { Check, Copy } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button, IconButton } from '../../../../components/ui/Button';
import { Modal } from '../../../../components/ui/Modal';
import * as S from './style';

function CopyBlock({ label, text }: { label: string; text: string }) {
  const { t } = useTranslation();
  const [copied, setCopied] = useState(false);
  return (
    <div>
      <S.Label>{label}</S.Label>
      <S.Code>
        <pre data-testid={`copy-${label}`}>{text}</pre>
        <IconButton
          label={copied ? t('common.copied') : `${t('common.copy')} ${label}`}
          onClick={async () => {
            await navigator.clipboard?.writeText(text);
            setCopied(true);
            window.setTimeout(() => setCopied(false), 1500);
          }}
        >
          {copied ? <Check /> : <Copy />}
        </IconButton>
      </S.Code>
    </div>
  );
}

type Props = { token: string; mcpUrl?: string; onClose: () => void };

/** A freshly created token in a dialog: shown once, with ready-to-paste MCP snippets. */
export function TokenReveal({ token, mcpUrl, onClose }: Props) {
  const { t } = useTranslation();
  const claude = mcpUrl
    ? `claude mcp add --transport http radicle ${mcpUrl} \\\n  --header "Authorization: Bearer ${token}"`
    : '';
  const json = mcpUrl
    ? JSON.stringify(
        {
          mcpServers: {
            radicle: { type: 'http', url: mcpUrl, headers: { Authorization: `Bearer ${token}` } },
          },
        },
        null,
        2,
      )
    : '';
  return (
    <Modal
      open
      width={640}
      onOpenChange={(open) => !open && onClose()}
      title={t('admin.tokenTitle')}
      footer={
        <Button variant="primary" onClick={onClose}>
          {t('admin.tokenDone')}
        </Button>
      }
    >
      <S.Box>
        <S.Warning>{t('admin.tokenOnce')}</S.Warning>
        <CopyBlock label={t('admin.token')} text={token} />
        {mcpUrl && (
          <>
            <CopyBlock label="Claude Code" text={claude} />
            <CopyBlock label="JSON" text={json} />
          </>
        )}
      </S.Box>
    </Modal>
  );
}
