import { createLink } from '@tanstack/react-router';
import { useTranslation } from 'react-i18next';
import { CategoryIcon } from '../../../../components/icons/CategoryIcon';
import { Badge, TicketKey } from '../../../../components/ui/Badge';
import type { Project } from '../../../../services/api/types';
import * as S from './style';

const Card = createLink(S.Card);

export function ProjectCard({ project }: { project: Project }) {
  const { t } = useTranslation();
  return (
    <Card to="/p/$key/board" params={{ key: project.key }} search={{}}>
      <S.Top>
        <TicketKey>{project.key}</TicketKey>
        <Badge tone={project.role === 'viewer' ? 'neutral' : 'accent'}>
          {t(`projects.roles.${project.role}`)}
        </Badge>
      </S.Top>
      <S.Name>{project.name}</S.Name>
      <S.Meta>
        <CategoryIcon category="in_progress" />
        {t('projects.openTickets', { count: project.open_tickets })}
        {project.archived && <Badge tone="warning">{t('projects.archived')}</Badge>}
      </S.Meta>
    </Card>
  );
}
