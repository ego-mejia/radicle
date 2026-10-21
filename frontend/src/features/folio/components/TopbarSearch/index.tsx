import { useQuery } from '@tanstack/react-query';
import { createLink, useNavigate } from '@tanstack/react-router';
import { useId, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Input } from '../../../../components/ui/Input';
import { useDebounced } from '../../../../hooks/useDebounced';
import { folioKeys, searchDocs } from '../../../../services/api/folio';
import { Snippet } from '../Snippet';
import { hitTarget } from '../Snippet/hitTarget';
import * as S from './style';

const OptionLink = createLink(S.Option);
const DEBOUNCE_MS = 150;

/** The Folio bar's search: results while you type, Enter for the full search page. */
export function TopbarSearch() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const listId = useId();
  const [text, setText] = useState('');
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(-1);
  const q = useDebounced(text.trim(), DEBOUNCE_MS);
  const { data } = useQuery({
    queryKey: folioKeys.search(q, 'hybrid', {}),
    queryFn: () => searchDocs(q, 'hybrid', {}, 5, false),
    enabled: q.length > 0,
  });
  const hits = q ? (data?.items ?? []) : [];
  const shown = open && q.length > 0;

  const close = () => {
    setOpen(false);
    setActive(-1);
  };
  const goTo = (index: number) => {
    const hit = hits[index];
    if (hit) {
      const { page, hash } = hitTarget(hit.url);
      void navigate({ to: '/folio/p/$page', params: { page }, hash });
    } else {
      void navigate({ to: '/folio/search', search: { q: text.trim() } });
    }
    close();
  };

  return (
    <S.Wrap>
      <Input
        type="search"
        role="combobox"
        aria-label={t('folio.search')}
        aria-expanded={shown}
        aria-controls={listId}
        aria-activedescendant={active >= 0 ? `${listId}-${active}` : undefined}
        placeholder={t('folio.searchPlaceholder')}
        value={text}
        onChange={(e) => {
          setText(e.target.value);
          setOpen(true);
          setActive(-1);
        }}
        onFocus={() => setOpen(true)}
        onBlur={() => setTimeout(close, 150)}
        onKeyDown={(e) => {
          if (e.key === 'ArrowDown') {
            e.preventDefault();
            setActive((i) => Math.min(i + 1, hits.length - 1));
          } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            setActive((i) => Math.max(i - 1, -1));
          } else if (e.key === 'Escape') {
            close();
          } else if (e.key === 'Enter' && text.trim()) {
            e.preventDefault();
            goTo(active);
          }
        }}
      />
      {shown && (
        <S.Panel>
          <S.List id={listId} role="listbox" aria-label={t('folio.searchPage.results')}>
            {hits.map((hit, i) => {
              const { page, hash } = hitTarget(hit.url);
              return (
                <li
                  key={hit.node_id}
                  id={`${listId}-${i}`}
                  role="option"
                  aria-selected={i === active}
                >
                  <OptionLink
                    to="/folio/p/$page"
                    params={{ page }}
                    hash={hash}
                    $active={i === active}
                    onClick={close}
                  >
                    <S.Title>{hit.title}</S.Title>
                    <S.Small>{[hit.space, ...hit.section].join(' › ')}</S.Small>
                    <S.Small>
                      <Snippet text={hit.snippet || hit.description} />
                    </S.Small>
                  </OptionLink>
                </li>
              );
            })}
          </S.List>
          <S.Footer>
            {data && hits.length === 0 ? t('folio.searchPage.none', { q }) : t('folio.searchEnter')}
          </S.Footer>
        </S.Panel>
      )}
    </S.Wrap>
  );
}
