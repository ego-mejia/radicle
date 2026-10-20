import * as Popover from '@radix-ui/react-popover';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Bookmark, Plus, X } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '../../../../components/ui/Button';
import { deleteFilter, fetchFilters, workKeys } from '../../../../services/api/work';
import type { SavedFilter } from '../../../../services/api/types';
import { SaveFilterModal } from '../SaveFilterModal';
import * as S from './style';

type Props = { project: string; query: string; onPick: (rql: string) => void };

/** Saved filters by visibility (mine, the project's and the instance's), in a dropdown. */
export function SavedFilters({ project, query, onPick }: Props) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [saving, setSaving] = useState(false);
  const { data: filters = [] } = useQuery({
    queryKey: workKeys.filters(project),
    queryFn: () => fetchFilters(project),
  });
  const remove = useMutation({
    mutationFn: deleteFilter,
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ['filters'] }),
  });
  const groups: { id: string; items: SavedFilter[] }[] = [
    { id: 'mine', items: filters.filter((f) => f.mine && f.visibility === 'private') },
    { id: 'project', items: filters.filter((f) => f.visibility === 'project') },
    { id: 'instance', items: filters.filter((f) => f.visibility === 'instance') },
  ];
  return (
    <Popover.Root>
      <Popover.Trigger asChild>
        <Button size="sm" data-tour="list.saved-filters">
          <Bookmark />
          {t('list.saved')}
        </Button>
      </Popover.Trigger>
      <Popover.Portal>
        <S.Panel align="end" sideOffset={6} aria-label={t('filters.title')}>
          <S.Head>
            <h2>{t('filters.title')}</h2>
            <Button size="sm" variant="ghost" onClick={() => setSaving(true)}>
              <Plus />
              {t('filters.saveShort')}
            </Button>
          </S.Head>
          {groups.map((group) => (
            <S.Group key={group.id}>
              <h3>{t(`filters.groups.${group.id}`)}</h3>
              {group.items.length === 0 ? (
                <S.Empty>—</S.Empty>
              ) : (
                group.items.map((f) => (
                  <S.Item key={f.id} $active={f.rql === query}>
                    <Popover.Close asChild>
                      <button type="button" title={f.rql} onClick={() => onPick(f.rql)}>
                        {f.name}
                      </button>
                    </Popover.Close>
                    {f.mine && (
                      <S.Remove
                        type="button"
                        aria-label={t('filters.delete', { name: f.name })}
                        onClick={() => remove.mutate(f.id)}
                      >
                        <X />
                      </S.Remove>
                    )}
                  </S.Item>
                ))
              )}
            </S.Group>
          ))}
        </S.Panel>
      </Popover.Portal>
      {saving && <SaveFilterModal project={project} rql={query} onClose={() => setSaving(false)} />}
    </Popover.Root>
  );
}
