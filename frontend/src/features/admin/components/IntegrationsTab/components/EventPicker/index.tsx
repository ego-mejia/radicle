import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { fetchPublicEvents, integrationKeys } from '../../../../../../services/api/integrations';
import * as S from './style';

type Props = { value: string[]; onChange: (next: string[]) => void };

/** Public events to pick; none picked means every event. */
export function EventPicker({ value, onChange }: Props) {
  const { t } = useTranslation();
  const { data: events = [] } = useQuery({
    queryKey: integrationKeys.events,
    queryFn: fetchPublicEvents,
  });
  const toggle = (name: string) =>
    onChange(value.includes(name) ? value.filter((n) => n !== name) : [...value, name]);
  return (
    <S.Box role="group" aria-label={t('integrations.events')}>
      {events.map((e) => (
        <label key={e.name} title={e.label}>
          <input type="checkbox" checked={value.includes(e.name)} onChange={() => toggle(e.name)} />
          <code>{e.name}</code>
        </label>
      ))}
      <S.Hint>{t('integrations.eventsHint')}</S.Hint>
    </S.Box>
  );
}
