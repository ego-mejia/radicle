import { useTranslation } from 'react-i18next';
import { Field } from '../../../../components/ui/Field';
import { Select } from '../../../../components/ui/Input';
import type { TicketTarget, TicketType } from '../../hooks/useTicketTarget';
import * as S from './style';

export function TicketTargetFields({ target }: { target: TicketTarget }) {
  const { t } = useTranslation();
  return (
    <>
      <S.Row>
        <Field label={t('folio.tickets.project')}>
          <Select value={target.project} onChange={(e) => target.setProject(e.target.value)}>
            {target.projects.map((p) => (
              <option key={p.key} value={p.key}>
                {p.key} · {p.name}
              </option>
            ))}
          </Select>
        </Field>
        <Field label={t('folio.tickets.type')}>
          <Select
            value={target.type}
            onChange={(e) => target.setType(e.target.value as TicketType)}
          >
            {(['task', 'bug', 'draft'] as const).map((kind) => (
              <option key={kind} value={kind}>
                {t(`folio.tickets.types.${kind}`)}
              </option>
            ))}
          </Select>
        </Field>
      </S.Row>
      <S.Row>
        <Field label={t('folio.tickets.area')} hint={t('folio.tickets.areaHint')}>
          <Select value={target.area} onChange={(e) => target.setArea(e.target.value)}>
            <option value="">{t('folio.tickets.none')}</option>
            {target.areas.map((a) => (
              <option key={a.name} value={a.name}>
                {a.name}
              </option>
            ))}
          </Select>
        </Field>
        <Field label={t('folio.tickets.milestone')}>
          <Select value={target.milestone} onChange={(e) => target.setMilestone(e.target.value)}>
            <option value="">{t('folio.tickets.none')}</option>
            {target.milestones.map((m) => (
              <option key={m.name} value={m.name}>
                {m.name}
              </option>
            ))}
          </Select>
        </Field>
      </S.Row>
    </>
  );
}
