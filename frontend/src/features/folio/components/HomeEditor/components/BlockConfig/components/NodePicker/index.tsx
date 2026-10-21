import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '../../../../../../../../components/ui/Button';
import { Field } from '../../../../../../../../components/ui/Field';
import { Input } from '../../../../../../../../components/ui/Input';
import { useDebounced } from '../../../../../../../../hooks/useDebounced';
import { fetchNode, folioKeys, searchDocs } from '../../../../../../../../services/api/folio';
import * as S from './style';

type Props = { node: string | null; error: string | null; onPick: (node: string | null) => void };

/** Pin a published page or post, or leave it empty for the newest labelled one. */
export function NodePicker({ node, error, onPick }: Props) {
  const { t } = useTranslation();
  const [text, setText] = useState('');
  const q = useDebounced(text.trim(), 200);
  const pinned = useQuery({
    queryKey: folioKeys.node(node ?? ''),
    queryFn: () => fetchNode(node ?? ''),
    enabled: Boolean(node),
  });
  const { data } = useQuery({
    queryKey: folioKeys.search(q, 'hybrid', {}),
    queryFn: () => searchDocs(q, 'hybrid', {}, 8, false),
    enabled: q.length > 0,
  });
  const seen = new Set<string>();
  const hits = (q ? (data?.items ?? []) : []).filter(
    (h) => !seen.has(h.node_id) && Boolean(seen.add(h.node_id)),
  );

  return (
    <>
      <S.Current>
        <span>
          {node
            ? t('folio.homeEditor.config.pinned', { title: pinned.data?.title ?? '…' })
            : t('folio.homeEditor.config.newest')}
        </span>
        {node && (
          <Button size="sm" variant="ghost" onClick={() => onPick(null)}>
            {t('folio.homeEditor.config.unpin')}
          </Button>
        )}
      </S.Current>
      <Field label={t('folio.homeEditor.config.pick')} error={error}>
        <Input type="search" value={text} onChange={(e) => setText(e.target.value)} />
      </Field>
      {hits.length > 0 && (
        <S.Hits>
          {hits.map((hit) => (
            <li key={hit.node_id}>
              <S.Hit
                type="button"
                onClick={() => {
                  onPick(hit.node_id);
                  setText('');
                }}
              >
                {hit.title}
                <small>{hit.space}</small>
              </S.Hit>
            </li>
          ))}
        </S.Hits>
      )}
    </>
  );
}
