import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { Field } from '../../../../../../components/ui/Field';
import { Select } from '../../../../../../components/ui/Input';
import { fetchProject, fetchProjects, projectKeys } from '../../../../../../services/api/projects';
import type { Field as Name, Metadata } from '../../validate';
import * as S from './style';

type Props = {
  value: Metadata;
  onChange: (value: Metadata) => void;
  errors: Partial<Record<Name, string>>;
};

/** Optional: the Docket project, milestones and areas this doc is about (Folio 4.4). Docket
 * lists the doc in each of those milestones and areas. */
export function DocketFields({ value, onChange, errors }: Props) {
  const { t } = useTranslation();
  const project = value.docket_project;
  const projects = useQuery({ queryKey: projectKeys.list(false), queryFn: () => fetchProjects() });
  const detail = useQuery({
    queryKey: projectKeys.detail(project),
    queryFn: () => fetchProject(project),
    enabled: !!project,
  });
  const milestones = (detail.data?.milestones ?? []).filter(
    (m) => m.status === 'open' || value.docket_milestones.includes(m.name),
  );
  const areas = (detail.data?.areas ?? []).filter(
    (a) => !a.archived || value.docket_areas.includes(a.name),
  );
  const toggle = (field: 'docket_milestones' | 'docket_areas', name: string, on: boolean) => {
    const rest = value[field].filter((n) => n !== name);
    onChange({ ...value, [field]: on ? [...rest, name] : rest });
  };
  const chosen = value.docket_milestones.length + value.docket_areas.length;

  return (
    <S.Box open={!!project}>
      <summary>
        {t('folio.publish.docket.title')}
        <S.Muted>
          {project
            ? t('folio.publish.docket.summary', { project, count: chosen })
            : t('folio.publish.docket.optional')}
        </S.Muted>
      </summary>
      <S.Inner>
        <Field
          label={t('folio.publish.docket.project')}
          error={errors.docket_project}
          hint={t('folio.publish.docket.hint')}
        >
          <Select
            value={project}
            invalid={Boolean(errors.docket_project)}
            onChange={(e) =>
              onChange({
                ...value,
                docket_project: e.target.value,
                docket_milestones: [],
                docket_areas: [],
              })
            }
          >
            <option value="">{t('folio.tickets.none')}</option>
            {(projects.data ?? []).map((p) => (
              <option key={p.key} value={p.key}>
                {p.key} · {p.name}
              </option>
            ))}
          </Select>
        </Field>
        {project && (
          <>
            <Field
              label={t('folio.publish.docket.milestones')}
              error={errors.docket_milestones}
              group
            >
              <S.Checks>
                {milestones.map((m) => (
                  <S.Check key={m.name}>
                    <input
                      type="checkbox"
                      checked={value.docket_milestones.includes(m.name)}
                      onChange={(e) => toggle('docket_milestones', m.name, e.target.checked)}
                    />
                    {m.name}
                  </S.Check>
                ))}
              </S.Checks>
            </Field>
            <Field label={t('folio.publish.docket.areas')} error={errors.docket_areas} group>
              <S.Checks>
                {areas.map((a) => (
                  <S.Check key={a.name}>
                    <input
                      type="checkbox"
                      checked={value.docket_areas.includes(a.name)}
                      onChange={(e) => toggle('docket_areas', a.name, e.target.checked)}
                    />
                    {a.name}
                  </S.Check>
                ))}
              </S.Checks>
            </Field>
          </>
        )}
      </S.Inner>
    </S.Box>
  );
}
