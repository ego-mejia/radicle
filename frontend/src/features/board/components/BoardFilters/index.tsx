import { X } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Button } from '../../../../components/ui/Button';
import { Select } from '../../../../components/ui/Input';
import type { BoardFilters as Filters } from '../../../../lib/rql';
import { TICKET_TYPES, type ProjectDetail } from '../../../../services/api/types';
import * as S from './style';

type Props = {
  project: ProjectDetail;
  tags: string[];
  value: Filters;
  onChange: (next: Filters) => void;
};

/** Filters live in the URL so a filtered board can be shared. */
export function BoardFilters({ project, tags, value, onChange }: Props) {
  const { t } = useTranslation();
  const set = (name: keyof Filters) => (e: React.ChangeEvent<HTMLSelectElement>) =>
    onChange({ ...value, [name]: e.target.value || undefined });
  const active = Object.values(value).some(Boolean);

  return (
    <S.Bar role="group" aria-label={t('board.filters')}>
      <Select value={value.type ?? ''} onChange={set('type')} aria-label={t('ticket.fields.type')}>
        <option value="">{t('board.allTypes')}</option>
        {TICKET_TYPES.map((type) => (
          <option key={type} value={type}>
            {t(`ticket.types.${type}`)}
          </option>
        ))}
      </Select>
      <Select value={value.area ?? ''} onChange={set('area')} aria-label={t('ticket.fields.area')}>
        <option value="">{t('board.allAreas')}</option>
        <option value="-">{t('ticket.noArea')}</option>
        {project.areas.map((a) => (
          <option key={a.name} value={a.name}>
            {a.name}
          </option>
        ))}
      </Select>
      <Select
        value={value.milestone ?? ''}
        onChange={set('milestone')}
        aria-label={t('ticket.fields.milestone')}
      >
        <option value="">{t('board.allMilestones')}</option>
        <option value="-">{t('ticket.noMilestone')}</option>
        {project.milestones.map((m) => (
          <option key={m.name} value={m.name}>
            {m.name}
          </option>
        ))}
      </Select>
      <Select
        value={value.assignee ?? ''}
        onChange={set('assignee')}
        aria-label={t('ticket.fields.assignee')}
      >
        <option value="">{t('board.everyone')}</option>
        <option value="me">{t('board.me')}</option>
        <option value="-">{t('ticket.unassigned')}</option>
        {project.members
          .filter((m) => m.role !== 'viewer')
          .map((m) => (
            <option key={m.handle} value={m.handle}>
              @{m.handle}
            </option>
          ))}
      </Select>
      <Select value={value.tag ?? ''} onChange={set('tag')} aria-label={t('ticket.fields.tags')}>
        <option value="">{t('board.allTags')}</option>
        {tags.map((tag) => (
          <option key={tag} value={tag}>
            #{tag}
          </option>
        ))}
      </Select>
      {active && (
        <Button size="sm" variant="ghost" onClick={() => onChange({})}>
          <X />
          {t('board.clear')}
        </Button>
      )}
    </S.Bar>
  );
}
