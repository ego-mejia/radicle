import { Download, Linkedin } from 'lucide-react';
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '../../../../components/ui/Button';
import { Modal } from '../../../../components/ui/Modal';
import { useToast } from '../../../../hooks/useToast';
import { fetchMilestoneRecap } from '../../../../services/api/projects';
import type { MilestoneRecap } from '../../../../services/api/types';
import { firstTime, recapStats, teamLine, TICKET_DONE, type TicketDone } from '../../lib/celebrate';
import { drawShareCard } from '../../lib/shareCard';
import { Confetti } from './components/Confetti';
import { RadiCheer } from './components/RadiCheer';
import { RecapStats } from './components/RecapStats';
import * as S from './style';

const LINKEDIN = 'https://www.linkedin.com/feed/?shareActive=true&text=';

/**
 * When the last ticket of a milestone reaches done: confetti, Radi cheering, the numbers
 * behind it, and a card to share on LinkedIn.
 */
export function MilestoneCelebration() {
  const { t } = useTranslation();
  const toast = useToast();
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
  const card = () =>
    drawShareCard({
      badge: t('celebration.badge'),
      title: recap.milestone,
      subtitle: recap.project_name,
      stats,
      footer: team,
      brand: t('celebration.brand'),
    });

  const download = async () => {
    const url = URL.createObjectURL(await card());
    const link = document.createElement('a');
    link.href = url;
    link.download = `${recap.project_key}-${recap.milestone}.png`.replace(/\s+/g, '-');
    link.click();
    URL.revokeObjectURL(url);
  };

  const share = async () => {
    // LinkedIn takes text from a link, not images: copy the card so it pastes into the post.
    // The tab opens first, while the click still counts as the user's.
    const post = window.open('about:blank', '_blank');
    try {
      const image = await card();
      await navigator.clipboard.write([new ClipboardItem({ 'image/png': image })]);
      toast(t('celebration.copied'), 'info');
    } catch {
      await download();
      toast(t('celebration.downloaded'), 'info');
    }
    const text = t('celebration.post', {
      ...vars,
      done: recap.done,
      bugs: recap.bugs,
      hours: Math.round(recap.minutes_logged / 60),
      team,
    });
    const url = LINKEDIN + encodeURIComponent(text);
    if (post) post.location.href = url;
    else window.open(url, '_blank', 'noopener');
  };

  return (
    <>
      <Confetti />
      <Modal
        open
        onOpenChange={(open) => !open && setRecap(null)}
        title={t('celebration.title')}
        width={560}
        footer={
          <>
            <Button onClick={() => void download()}>
              <Download size={14} /> {t('celebration.download')}
            </Button>
            <Button variant="primary" onClick={() => void share()}>
              <Linkedin size={14} /> {t('celebration.share')}
            </Button>
          </>
        }
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
    </>
  );
}
