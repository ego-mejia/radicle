import * as Popover from '@radix-ui/react-popover';
import { useTranslation } from 'react-i18next';
import { Avatar } from '../../../../components/ui/Avatar';
import type { SpaceParticipant } from '../../../../services/api/folioSpaces';
import * as S from './style';

const SHOWN = 4;

type Props = {
  participants: SpaceParticipant[];
  everyoneRole?: SpaceParticipant['role'] | null;
};

/** Who takes part in a space, admins first with a lime ring; opens the full list. */
export function ParticipantsStack({ participants, everyoneRole }: Props) {
  const { t } = useTranslation();
  const admins = participants.filter((p) => p.role === 'admin').length;
  const others = participants.length - admins;
  const extra = participants.length - SHOWN;
  const summary = t('folio.spaceHome.people.summary', { admins, count: others });
  return (
    <Popover.Root>
      <Popover.Trigger asChild>
        <S.Trigger type="button" aria-label={t('folio.spaceHome.people.open', { summary })}>
          <S.Stack>
            {participants.slice(0, SHOWN).map((p) => (
              <S.Ring key={p.handle} $admin={p.role === 'admin'}>
                <Avatar
                  handle={p.handle}
                  name={p.name}
                  kind={p.kind === 'agent' ? 'agent' : 'human'}
                  size={26}
                />
              </S.Ring>
            ))}
            {extra > 0 && <S.More>+{extra}</S.More>}
          </S.Stack>
          <S.Summary>
            <b>{t('folio.spaceHome.people.admins', { count: admins })}</b>
            {' · '}
            {t('folio.spaceHome.people.others', { count: others })}
          </S.Summary>
        </S.Trigger>
      </Popover.Trigger>
      <Popover.Portal>
        <S.Content align="center" sideOffset={8} aria-label={t('folio.spaceHome.people.title')}>
          {(['admin', 'editor', 'reader'] as const).map((role) => {
            const people = participants.filter((p) => p.role === role);
            if (!people.length) return null;
            return (
              <S.Group key={role}>
                <S.GroupTitle>{t(`folio.spaceHome.people.role.${role}`)}</S.GroupTitle>
                {people.map((p) => (
                  <S.Person key={p.handle}>
                    <Avatar
                      handle={p.handle}
                      name={p.name}
                      kind={p.kind === 'agent' ? 'agent' : 'human'}
                      size={24}
                    />
                    <span>{p.name}</span>
                    <small>@{p.handle}</small>
                  </S.Person>
                ))}
              </S.Group>
            );
          })}
          {everyoneRole && (
            <S.Everyone>{t(`folio.spaceHome.people.everyone.${everyoneRole}`)}</S.Everyone>
          )}
        </S.Content>
      </Popover.Portal>
    </Popover.Root>
  );
}
