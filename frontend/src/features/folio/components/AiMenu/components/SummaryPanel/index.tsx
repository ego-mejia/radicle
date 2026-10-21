import { useMutation } from '@tanstack/react-query';
import type { Editor } from '@tiptap/react';
import { useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { MarkdownView } from '../../../../../../components/Markdown/MarkdownView';
import { Button } from '../../../../../../components/ui/Button';
import { Spinner } from '../../../../../../components/ui/Spinner';
import { useErrorMessage } from '../../../../../../hooks/useErrorMessage';
import { summarizePage } from '../../../../../../services/api/folioAi';
import { fromText } from '../../../../editor/fromText';
import { BlockPanel } from '../../../BlockPanel';
import * as S from './style';

type Props = { editor: Editor; nodeId: string; onClose: () => void };

/** The page's summary from the AI. It only lands in the page if you insert it. */
export function SummaryPanel({ editor, nodeId, onClose }: Props) {
  const { t } = useTranslation();
  const errorMessage = useErrorMessage();
  const summary = useMutation({ mutationFn: () => summarizePage(nodeId) });
  const { mutate } = summary;
  useEffect(() => mutate(), [mutate]);

  const insert = (text: string) => {
    editor
      .chain()
      .focus('start')
      .insertContent([
        {
          type: 'heading',
          attrs: { level: 2 },
          content: [{ type: 'text', text: t('folio.ai.summaryHeading') }],
        },
        ...fromText(text),
      ])
      .run();
    onClose();
  };

  return (
    <BlockPanel title={t('folio.ai.summaryTitle')} onClose={onClose}>
      {summary.isPending && (
        <S.Waiting role="status">
          <Spinner />
          {t('folio.ai.thinking')}
        </S.Waiting>
      )}
      {summary.isError && <S.Error role="alert">{errorMessage(summary.error)}</S.Error>}
      {summary.data && (
        <S.Proposal>
          <MarkdownView readOnly>{summary.data}</MarkdownView>
        </S.Proposal>
      )}
      <S.Note>{t('folio.ai.proposalNote')}</S.Note>
      <S.Actions>
        <Button onClick={() => summary.mutate()} disabled={summary.isPending}>
          {t('folio.ai.again')}
        </Button>
        <Button
          variant="primary"
          disabled={!summary.data}
          onClick={() => summary.data && insert(summary.data)}
        >
          {t('folio.ai.insertSummary')}
        </Button>
      </S.Actions>
    </BlockPanel>
  );
}
