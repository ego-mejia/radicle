import type { Editor } from '@tiptap/react';
import { ListCollapse, Sparkles } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '../../../../components/ui/Button';
import { Menu } from '../../../../components/ui/Menu';
import { useEditorAi } from '../../hooks/useEditorAi';
import { SummaryPanel } from './components/SummaryPanel';

type Props = { editor: Editor; nodeId: string; space: string };

/** The editor's AI button (Folio 4.6): summarize the page in a side panel. Hidden without
 * a provider or with AI off in the space. */
export function AiMenu({ editor, nodeId, space }: Props) {
  const { t } = useTranslation();
  const available = useEditorAi(space);
  const [summary, setSummary] = useState(false);
  if (!available) return null;
  return (
    <>
      <Menu
        align="end"
        trigger={
          <Button variant="ghost">
            <Sparkles aria-hidden size={16} />
            {t('folio.ai.button')}
          </Button>
        }
        items={[
          {
            key: 'summarize',
            label: t('folio.ai.summarize'),
            icon: <ListCollapse aria-hidden size={16} />,
            onSelect: () => setSummary(true),
          },
        ]}
      />
      {summary && (
        <SummaryPanel editor={editor} nodeId={nodeId} onClose={() => setSummary(false)} />
      )}
    </>
  );
}
