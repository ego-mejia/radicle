import { Search } from 'lucide-react';
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '../../../../components/ui/Button';
import { suggest, type Suggestion } from '../../../../lib/rqlAssist';
import type { SearchFields } from '../../../../services/api/types';
import * as S from './style';

type Props = {
  value: string;
  onSubmit: (query: string) => void;
  fields: SearchFields | undefined;
  error?: { message: string; position: number } | null;
  warnings?: string[];
};

/** RQL input with field, operator and value completion; errors are underlined in place. */
export function RqlBar({ value, onSubmit, fields, error, warnings = [] }: Props) {
  const { t } = useTranslation();
  const [text, setText] = useState(value);
  const [items, setItems] = useState<Suggestion[]>([]);
  const [from, setFrom] = useState(0);
  const [active, setActive] = useState(0);

  useEffect(() => setText(value), [value]);

  const refresh = (next: string, caret: number) => {
    if (caret !== next.length) {
      setItems([]);
      return;
    }
    const result = suggest(next, fields);
    setItems(result.items);
    setFrom(result.from);
    setActive(0);
  };

  const accept = (item: Suggestion) => {
    const next = text.slice(0, from) + item.insert;
    setText(next);
    refresh(next, next.length);
  };

  const onKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (!items.length) return;
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      e.preventDefault();
      const delta = e.key === 'ArrowDown' ? 1 : -1;
      setActive((i) => (i + delta + items.length) % items.length);
    } else if (e.key === 'Tab') {
      e.preventDefault();
      accept(items[active]!);
    } else if (e.key === 'Escape') {
      setItems([]);
    }
  };

  const pos = error ? Math.min(error.position, text.length) : -1;
  const tokenEnd = pos >= 0 ? pos + Math.max(1, /^\S*/.exec(text.slice(pos))![0].length) : -1;

  return (
    <>
      <S.Wrap
        role="search"
        onSubmit={(e) => {
          e.preventDefault();
          setItems([]);
          onSubmit(text.trim());
        }}
      >
        <S.Field>
          <S.Mirror aria-hidden>
            {pos >= 0 ? (
              <>
                {text.slice(0, pos)}
                <mark>{text.slice(pos, tokenEnd) || ' '}</mark>
              </>
            ) : null}
          </S.Mirror>
          <S.Input
            value={text}
            $invalid={!!error}
            aria-label={t('list.rqlLabel')}
            data-tour="list.rql"
            aria-invalid={!!error || undefined}
            aria-describedby={error ? 'rql-error' : undefined}
            placeholder={t('list.rqlPlaceholder')}
            spellCheck={false}
            autoComplete="off"
            onChange={(e) => {
              setText(e.target.value);
              refresh(e.target.value, e.target.selectionStart ?? e.target.value.length);
            }}
            onKeyDown={onKeyDown}
            onFocus={(e) => refresh(text, e.target.selectionStart ?? text.length)}
            onBlur={() => window.setTimeout(() => setItems([]), 120)}
          />
          {items.length > 0 && (
            <S.Suggestions role="listbox">
              {items.map((item, i) => (
                <S.Suggestion
                  key={item.label}
                  role="option"
                  aria-selected={i === active}
                  $active={i === active}
                  onMouseDown={(e) => {
                    e.preventDefault();
                    accept(item);
                  }}
                >
                  {item.label}
                  {item.detail && <small>{item.detail}</small>}
                </S.Suggestion>
              ))}
            </S.Suggestions>
          )}
        </S.Field>
        <Button type="submit" variant="primary">
          <Search />
          {t('common.search')}
        </Button>
      </S.Wrap>
      {error && (
        <S.Error id="rql-error" role="alert">
          {error.message}
        </S.Error>
      )}
      {warnings.map((w) => (
        <S.Warning key={w}>{w}</S.Warning>
      ))}
    </>
  );
}
