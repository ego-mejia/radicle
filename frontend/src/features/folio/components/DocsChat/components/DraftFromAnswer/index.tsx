import { useMutation } from '@tanstack/react-query';
import { Link, useParams } from '@tanstack/react-router';
import { FilePlus2 } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Button } from '../../../../../../components/ui/Button';
import { useErrorMessage } from '../../../../../../hooks/useErrorMessage';
import { createNode, fetchPersonalSpace, saveDraft } from '../../../../../../services/api/folio';
import type { ChatMessage } from '../../../../../../services/api/folioChat';
import * as S from './style';

type Props = { question: string; message: ChatMessage };

/** "Write a draft with this": a new page in the space you're in (or your personal space)
 * with the answer and its sources. It stays a draft until you publish it, and an agent's
 * draft still goes through the approval queue. */
export function DraftFromAnswer({ question, message }: Props) {
  const { t } = useTranslation();
  const errorMessage = useErrorMessage();
  const { key } = useParams({ strict: false }) as { key?: string };
  const make = useMutation({
    mutationFn: async () => {
      const space = key ?? (await fetchPersonalSpace()).key;
      const title =
        question.trim().replace(/[?¿]/g, '').slice(0, 120) || t('folio.radi.draftTitle');
      const node = await createNode({ space, kind: 'page', title });
      const sources = message.citations.map((c) => `- [${c.title}](${c.url})`).join('\n');
      const content_md = sources
        ? `${message.content}\n\n## ${t('folio.chat.sources')}\n\n${sources}\n`
        : message.content;
      await saveDraft(node.id, { content_md });
      return { node, space };
    },
  });

  if (make.data) {
    const { node } = make.data;
    return (
      <S.Done role="status">
        <span>
          <strong>{t('folio.radi.draftReady')}</strong> “{node.title}”
        </span>
        <S.Tool>create_page · {t('folio.radi.draft')}</S.Tool>
        <Link to="/folio/p/$page/edit" params={{ page: `${node.id}-${node.slug}` }}>
          {t('folio.radi.openDraft')}
        </Link>
      </S.Done>
    );
  }
  return (
    <S.Wrap>
      <Button size="sm" variant="secondary" onClick={() => make.mutate()} disabled={make.isPending}>
        <FilePlus2 aria-hidden />
        {t('folio.radi.writeDraft')}
      </Button>
      {make.isError && <S.Error role="alert">{errorMessage(make.error)}</S.Error>}
    </S.Wrap>
  );
}
