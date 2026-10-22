import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link, useNavigate } from '@tanstack/react-router';
import { Eye, EyeOff, Plus, Search } from 'lucide-react';
import { type FormEvent, useState } from 'react';
import { Trans, useTranslation } from 'react-i18next';
import { useToast } from '../../../../hooks/useToast';
import type { FolioSpace } from '../../../../services/api/folio';
import { fetchWatching, setWatching, socialKeys } from '../../../../services/api/folioSocial';
import {
  fetchSpaceOverview,
  spaceKeys,
  type SpaceSectionKey,
} from '../../../../services/api/folioSpaces';
import { SECTIONS } from '../../sections';
import { ParticipantsStack } from '../ParticipantsStack';
import * as S from './style';

type Props = {
  space: FolioSpace;
  /** `all` is the space's portada; a section key shows that section's hero. */
  active: 'all' | SpaceSectionKey;
  /** What "Escribir aquí" or the section's button does; hidden without it. */
  onWrite?: () => void;
  /** Search inside the section instead of going to the search page. */
  onSearch?: (q: string) => void;
  query?: string;
};

/** The dark band on top of a space and its sections (RAD-57): title, people, a search
 * limited to the space, and the pills that move between sections. */
export function SpaceHero({ space, active, onWrite, onSearch, query = '' }: Props) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [draft, setDraft] = useState(query);
  const overview = useQuery({
    queryKey: spaceKeys.overview(space.key),
    queryFn: () => fetchSpaceOverview(space.key),
  });
  const sections = (overview.data?.sections ?? []).filter((s) => s.visible);
  const all = sections.reduce((n, s) => n + s.count, 0);
  const isSection = active !== 'all';
  const title = isSection ? t(`folio.sections.${active}.title`) : space.name;
  const description = isSection ? t(`folio.sections.${active}.description`) : space.description;
  const placeholder = isSection
    ? t(`folio.sections.${active}.search`)
    : t('folio.spaceHome.search', { space: space.name });
  const isAdmin = space.permissions.includes('admin');

  const submit = (event: FormEvent) => {
    event.preventDefault();
    const q = draft.trim();
    if (onSearch) return onSearch(q);
    if (q) void navigate({ to: '/folio/search', search: { q, space: space.key } });
  };

  return (
    <S.Hero>
      <S.Top>
        {isSection ? (
          <S.Crumbs aria-label={t('folio.sections.crumbLabel')}>
            <Link to="/folio/s/$key" params={{ key: space.key }}>
              {space.name}
            </Link>
            <span aria-hidden>/</span>
            <S.Here aria-current="page">{title}</S.Here>
          </S.Crumbs>
        ) : (
          <S.Kicker>{t('folio.spaceHome.kicker')}</S.Kicker>
        )}
        <S.Actions>
          {!isSection && <FollowButton space={space} />}
          {isAdmin && (
            <S.GhostLink to={`/folio/s/${space.key}/admin`}>
              {t('folio.spaceHome.manage')}
            </S.GhostLink>
          )}
          {onWrite && (
            <S.Primary type="button" onClick={onWrite}>
              <Plus aria-hidden />
              {isSection ? t(`folio.sections.${active}.cta`) : t('folio.spaceHome.write')}
            </S.Primary>
          )}
        </S.Actions>
      </S.Top>

      <S.Middle>
        <h1>{title}</h1>
        {description && <p>{description}</p>}
        {!isSection && overview.data && (
          <S.Stats>
            <span>
              <Trans
                i18nKey="folio.spaceHome.pages"
                count={overview.data.pages}
                components={{ b: <b /> }}
              />
            </span>
            <span>
              <Trans
                i18nKey="folio.spaceHome.folders"
                count={overview.data.folders}
                components={{ b: <b /> }}
              />
            </span>
            {overview.data.participants.length > 0 && (
              <ParticipantsStack
                participants={overview.data.participants}
                everyoneRole={overview.data.everyone_role}
              />
            )}
          </S.Stats>
        )}
        <S.Search role="search" onSubmit={submit}>
          <Search aria-hidden />
          <input
            type="search"
            value={draft}
            placeholder={placeholder}
            aria-label={t('folio.spaceHome.searchLabel', { space: title })}
            onChange={(e) => {
              setDraft(e.target.value);
              onSearch?.(e.target.value);
            }}
          />
          <button type="submit">{t('folio.spaceHome.searchButton')}</button>
        </S.Search>
        {sections.length > 0 && (
          <S.Pills aria-label={t('folio.spaceHome.sections', { space: space.name })}>
            <S.Pill
              to={`/folio/s/${space.key}`}
              $on={!isSection}
              aria-current={!isSection ? 'page' : undefined}
            >
              {t('folio.spaceHome.all')} <small>{all}</small>
            </S.Pill>
            {sections.map((s) => (
              <S.Pill
                key={s.key}
                to={`/folio/s/${space.key}/${SECTIONS[s.key].path}`}
                $on={active === s.key}
                aria-current={active === s.key ? 'page' : undefined}
              >
                {t(`folio.sections.${s.key}.label`)} <small>{s.count}</small>
              </S.Pill>
            ))}
          </S.Pills>
        )}
      </S.Middle>
    </S.Hero>
  );
}

function FollowButton({ space }: { space: FolioSpace }) {
  const { t } = useTranslation();
  const toast = useToast();
  const queryClient = useQueryClient();
  const key = socialKeys.watch('space', space.id);
  const watching = useQuery({ queryKey: key, queryFn: () => fetchWatching('space', space.id) });
  const toggle = useMutation({
    mutationFn: (on: boolean) => setWatching('space', space.id, on),
    onSuccess: (_, on) => {
      queryClient.setQueryData(key, on);
      toast(
        t(on ? 'folio.spaceHome.followed' : 'folio.spaceHome.unfollowed', { space: space.name }),
      );
    },
  });
  const on = watching.data === true;
  return (
    <S.Ghost type="button" aria-pressed={on} onClick={() => toggle.mutate(!on)}>
      {on ? <EyeOff aria-hidden /> : <Eye aria-hidden />}
      {on ? t('folio.spaceHome.following') : t('folio.spaceHome.follow')}
    </S.Ghost>
  );
}
