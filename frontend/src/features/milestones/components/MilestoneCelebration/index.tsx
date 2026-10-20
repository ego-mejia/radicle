import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Modal } from '../../../../components/ui/Modal';
import { fetchMilestoneRecap } from '../../../../services/api/projects';
import type { MilestoneRecap } from '../../../../services/api/types';
import { firstTime, recapStats, teamLine, TICKET_DONE, type TicketDone } from '../../lib/celebrate';
import { RadiCheer } from './components/RadiCheer';
import { RecapStats } from './components/RecapStats';
import * as S from './style';

/** When the last ticket of a milestone reaches done: Radi cheering and the numbers behind it. */
export function MilestoneCelebration() {
  const { t } = useTranslation();
  const [recap, setRecap] = useState<MilestoneRecap | null>(null);

  useEffect(() => {
    const onDone = (e: Event) => {
      const { project, milestone } = (e as CustomEvent<TicketDone>).detail;
      fetchMilestoneRecap(project, milestone)
        .then((r) => {
          if (r.complete && firstTime(r.project_key, r.milestone)) setRecap(r);
        })
        .catch(() => {}); // a missed party is not an error worth a toast
    };
    window.addEventListener(TICKET_DONE, onDone);
    return () => window.removeEventListener(TICKET_DONE, onDone);
  }, []);

  if (!recap) return null;
  const stats = recapStats(recap, t);
  const team = teamLine(recap, t);
  const vars = { milestone: recap.milestone, project: recap.project_name };

  return (
    <Modal
      open
      onOpenChange={(open) => !open && setRecap(null)}
      title={t('celebration.title')}
      width={560}
    >
      <S.Hero>
        <RadiCheer />
        <S.Headline>{t('celebration.headline', vars)}</S.Headline>
        <S.Thanks>
          {t(recap.on_time ? 'celebration.thanksOnTime' : 'celebration.thanks', vars)}
        </S.Thanks>
      </S.Hero>
      <RecapStats recap={recap} stats={stats} team={team} />
    </Modal>
  );
}
