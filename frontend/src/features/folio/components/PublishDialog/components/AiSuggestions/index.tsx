import { useQuery } from '@tanstack/react-query';
import { Sparkles } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '../../../../../../components/ui/Button';
import type { FolioSchema } from '../../../../../../services/api/folio';
import { suggestMetadata } from '../../../../../../services/api/folioAi';
import { useEditorAi } from '../../../../hooks/useEditorAi';
import type { Metadata } from '../../validate';
import * as S from './style';

type Props = {
  nodeId: string;
  space: string;
  value: Metadata;
  schema: FolioSchema;
  /** Fills one field; the person still publishes. */
  onUse: (patch: Partial<Metadata>) => void;
};

/** The AI's description, labels and type for the empty fields (Folio 4.6), each accepted on
 * its own. Asked once when the dialog opens with any of them empty. */
export function AiSuggestions({ nodeId, space, value, schema, onUse }: Props) {
  const { t } = useTranslation();
  const available = useEditorAi(space);
  const [empty] = useState(
    () => !value.description.trim() || !value.labels.length || !value.doc_type,
  );
  const suggestion = useQuery({
    queryKey: ['folio', 'ai', 'metadata', nodeId],
    queryFn: () => suggestMetadata(nodeId),
    enabled: available && empty,
    staleTime: Infinity,
    retry: false,
  });
  const s = suggestion.data;
  if (!available || !empty) return null;
  if (suggestion.isPending) {
    return (
      <S.Box role="status">
        <Sparkles aria-hidden />
        {t('folio.ai.suggesting')}
      </S.Box>
    );
  }
  const docType = schema.doc_types.find((d) => d.key === s?.doc_type);
  const rows = [
    !value.description.trim() &&
      s?.description && {
        key: 'description',
        label: t('folio.publish.description'),
        text: s.description,
        use: { description: s.description },
      },
    !value.labels.length &&
      s?.labels.length && {
        key: 'labels',
        label: t('folio.publish.labels'),
        text: s.labels.join(', '),
        use: { labels: s.labels },
      },
    !value.doc_type &&
      docType && {
        key: 'doc_type',
        label: t('folio.publish.docType'),
        text: docType.name,
        use: { doc_type: docType.key },
      },
  ].filter(Boolean) as { key: string; label: string; text: string; use: Partial<Metadata> }[];
  if (!rows.length) return null;

  return (
    <S.Box as="section" aria-label={t('folio.ai.suggestions')}>
      <S.Title>
        <Sparkles aria-hidden />
        {t('folio.ai.suggestions')}
      </S.Title>
      {rows.map((row) => (
        <S.Row key={row.key}>
          <div>
            <S.Label>{row.label}</S.Label>
            <S.Text>{row.text}</S.Text>
          </div>
          <Button
            size="sm"
            aria-label={t('folio.ai.use', { field: row.label })}
            onClick={() => onUse(row.use)}
          >
            {t('folio.ai.useShort')}
          </Button>
        </S.Row>
      ))}
    </S.Box>
  );
}
