import * as Popover from '@radix-ui/react-popover';
import { Check, ChevronDown } from 'lucide-react';
import { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import * as S from './style';

export type FilterOption = { value: string; label: string; count?: number };

type Props = {
  /** What it filters, e.g. "Project". */
  label: string;
  options: FilterOption[];
  selected: string[];
  onChange: (values: string[]) => void;
  /** Several values at once (features); otherwise one, with an "all" choice. */
  multi?: boolean;
  /** The choice that clears the filter in single mode, e.g. "All projects". */
  allLabel?: string;
  /** Shown instead of the options, e.g. "Pick a project first". */
  hint?: string;
  /** With many options: a search box, the chosen ones first, then the `top` most used. */
  searchable?: boolean;
  top?: number;
};

/** A filter button for the section tables (RAD-57). It stays usable with hundreds of
 * options: chosen ones first, the most used next, and a search for the rest. */
export function FilterPicker({
  label,
  options,
  selected,
  onChange,
  multi = false,
  allLabel,
  hint,
  searchable = false,
  top = 5,
}: Props) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const byValue = useMemo(() => new Map(options.map((o) => [o.value, o])), [options]);
  const summary = !selected.length
    ? t('folio.filters.all')
    : selected.length === 1
      ? (byValue.get(selected[0] ?? '')?.label ?? selected[0])
      : t('folio.filters.chosen', { count: selected.length });

  const q = query.trim().toLowerCase();
  const chosen = options.filter((o) => selected.includes(o.value));
  const rest = options
    .filter((o) => !selected.includes(o.value) && o.label.toLowerCase().includes(q))
    .sort((a, b) => (b.count ?? 0) - (a.count ?? 0));
  const shown = searchable && !q ? rest.slice(0, top) : rest;
  const hidden = rest.length - shown.length;

  const pick = (value: string) => {
    if (!multi) {
      onChange(value ? [value] : []);
      setOpen(false);
      return;
    }
    onChange(selected.includes(value) ? selected.filter((v) => v !== value) : [...selected, value]);
  };

  const row = (o: FilterOption) => {
    const on = selected.includes(o.value);
    return (
      <S.Option
        key={o.value}
        type="button"
        role={multi ? 'menuitemcheckbox' : 'menuitemradio'}
        aria-checked={on}
        $on={on}
        onClick={() => pick(o.value)}
      >
        {multi ? <S.Box $on={on}>{on ? <Check aria-hidden /> : null}</S.Box> : null}
        <span>{o.label}</span>
        {o.count !== undefined ? <S.Count>{o.count}</S.Count> : null}
      </S.Option>
    );
  };

  return (
    <Popover.Root
      open={open}
      onOpenChange={(next) => {
        setOpen(next);
        if (!next) setQuery('');
      }}
    >
      <Popover.Trigger asChild>
        <S.Trigger type="button" $active={selected.length > 0}>
          {label}: {summary}
          <ChevronDown aria-hidden />
        </S.Trigger>
      </Popover.Trigger>
      <Popover.Portal>
        <S.Content align="start" sideOffset={6} aria-label={label} role="menu">
          {hint ? (
            <S.Hint>{hint}</S.Hint>
          ) : (
            <>
              {searchable ? (
                <S.Search
                  type="search"
                  value={query}
                  autoFocus
                  aria-label={t('folio.filters.search', { count: options.length })}
                  placeholder={t('folio.filters.search', { count: options.length })}
                  onChange={(e) => setQuery(e.target.value)}
                />
              ) : null}
              {!multi && allLabel ? (
                <S.Option
                  type="button"
                  role="menuitemradio"
                  aria-checked={!selected.length}
                  $on={!selected.length}
                  onClick={() => pick('')}
                >
                  <span>{allLabel}</span>
                </S.Option>
              ) : null}
              {searchable && chosen.length ? (
                <>
                  <S.Label>{t('folio.filters.selected')}</S.Label>
                  {chosen.map(row)}
                </>
              ) : null}
              {searchable ? (
                <S.Label>{q ? t('folio.filters.results') : t('folio.filters.mostUsed')}</S.Label>
              ) : null}
              {(searchable ? shown : options).map(row)}
              {searchable && !shown.length ? <S.Hint>{t('folio.filters.none')}</S.Hint> : null}
              {hidden > 0 ? (
                <S.Hint>{t('folio.filters.searchForMore', { count: hidden })}</S.Hint>
              ) : null}
            </>
          )}
        </S.Content>
      </Popover.Portal>
    </Popover.Root>
  );
}
