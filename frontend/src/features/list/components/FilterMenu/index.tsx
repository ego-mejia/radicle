import * as Popover from '@radix-ui/react-popover';
import { ListFilter, X } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Button } from '../../../../components/ui/Button';
import {
  FILTER_FIELDS,
  filterCount,
  NO_FILTERS,
  type ListFilters,
} from '../../../../lib/listFilters';
import { PRIORITIES, type ProjectDetail } from '../../../../services/api/types';
import * as S from './style';

type Props = { project: ProjectDetail; value: ListFilters; onChange: (next: ListFilters) => void };
type Option = { value: string; label: string };

/** The Filter button: pick types, statuses, priorities, people, areas and milestones. */
export function FilterMenu({ project, value, onChange }: Props) {
  const { t } = useTranslation();
  const options: Record<keyof ListFilters, Option[]> = {
    type: ['task', 'bug', 'draft'].map((v) => ({ value: v, label: t(`ticket.types.${v}`) })),
    category: ['todo', 'in_progress', 'done'].map((v) => ({
      value: v,
      label: t(`ticket.categories.${v}`),
    })),
    priority: PRIORITIES.map((v) => ({ value: v, label: t(`ticket.priorities.${v}`) })),
    assignee: [
      { value: '@me', label: t('list.filter.me') },
      { value: '@none', label: t('list.filter.unassigned') },
      ...project.members.map((m) => ({ value: m.handle, label: m.display_name })),
    ],
    area: project.areas.filter((a) => !a.archived).map((a) => ({ value: a.name, label: a.name })),
    milestone: project.milestones.map((m) => ({ value: m.name, label: m.name })),
  };
  const toggle = (field: keyof ListFilters, v: string) => {
    const has = value[field].includes(v);
    onChange({
      ...value,
      [field]: has ? value[field].filter((x) => x !== v) : [...value[field], v],
    });
  };
  const count = filterCount(value);
  const labelOf = (field: keyof ListFilters, v: string) =>
    options[field].find((o) => o.value === v)?.label ?? v;

  return (
    <S.Wrap>
      <Popover.Root>
        <Popover.Trigger asChild>
          <Button size="sm" variant={count ? 'primary' : 'secondary'} data-tour="list.filter">
            <ListFilter />
            {t('list.filter.button')}
            {count > 0 && <S.Badge>{count}</S.Badge>}
          </Button>
        </Popover.Trigger>
        <Popover.Portal>
          <S.Panel align="start" sideOffset={6} aria-label={t('list.filter.button')}>
            {FILTER_FIELDS.map(
              (field) =>
                options[field].length > 0 && (
                  <S.Section key={field}>
                    <h3>{t(`list.filter.fields.${field}`)}</h3>
                    <S.Chips>
                      {options[field].map((o) => (
                        <S.Chip
                          key={o.value}
                          type="button"
                          aria-pressed={value[field].includes(o.value)}
                          onClick={() => toggle(field, o.value)}
                        >
                          {o.label}
                        </S.Chip>
                      ))}
                    </S.Chips>
                  </S.Section>
                ),
            )}
            <S.Footer>
              <Button
                size="sm"
                variant="ghost"
                disabled={!count}
                onClick={() => onChange(NO_FILTERS)}
              >
                {t('list.filter.clear')}
              </Button>
              <Popover.Close asChild>
                <Button size="sm" variant="primary">
                  {t('common.close')}
                </Button>
              </Popover.Close>
            </S.Footer>
          </S.Panel>
        </Popover.Portal>
      </Popover.Root>
      {FILTER_FIELDS.flatMap((field) =>
        value[field].map((v) => (
          <S.Active key={`${field}:${v}`}>
            <span>
              {t(`list.filter.fields.${field}`)}: <b>{labelOf(field, v)}</b>
            </span>
            <button
              type="button"
              aria-label={t('list.filter.remove', { value: labelOf(field, v) })}
              onClick={() => toggle(field, v)}
            >
              <X size={12} />
            </button>
          </S.Active>
        )),
      )}
    </S.Wrap>
  );
}
