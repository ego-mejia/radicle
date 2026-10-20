import { createLink } from '@tanstack/react-router';
import { Pencil } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { CategoryIcon } from '../../../../components/icons/CategoryIcon';
import { Badge, TicketKey } from '../../../../components/ui/Badge';
import { IconButton } from '../../../../components/ui/Button';
import type { Project } from '../../../../services/api/types';
import * as S from './style';

const Card = createLink(S.Card);

type Props = { project: Project; onEdit?: () => void };

/** A project tile; with `onEdit`, a pencil opens its edit dialog. */
export function ProjectCard({ project, onEdit }: Props) {
  const { t } = useTranslation();
  return (
    <S.Wrap>
      <Card to="/p/$key/board" params={{ key: project.key }} search={{}}>
        <S.Top>
          <TicketKey>{project.key}</TicketKey>
          <S.Role $room={Boolean(onEdit)}>
            <Badge tone={project.role === 'viewer' ? 'neutral' : 'accent'}>
              {t(`projects.roles.${project.role}`)}
            </Badge>
          </S.Role>
        </S.Top>
        <S.Name>{project.name}</S.Name>
        <S.Meta>
          <CategoryIcon category="in_progress" />
          {t('projects.openTickets', { count: project.open_tickets })}
          {project.archived && <Badge tone="warning">{t('projects.archived')}</Badge>}
        </S.Meta>
      </Card>
      {onEdit && (
        <S.Edit>
          <IconButton label={t('projects.editTitle', { key: project.key })} onClick={onEdit}>
            <Pencil />
          </IconButton>
        </S.Edit>
      )}
    </S.Wrap>
  );
}
