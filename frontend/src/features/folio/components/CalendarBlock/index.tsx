import { useQuery } from '@tanstack/react-query';
import { NodeViewWrapper, type NodeViewProps } from '@tiptap/react';
import { CalendarDays } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Button } from '../../../../components/ui/Button';
import { Select } from '../../../../components/ui/Input';
import { calendarKeys, fetchCalendars } from '../../../../services/api/folioCalendars';
import type { CalendarMode } from '../../calendar/dates';
import { CalendarEmbed } from '../CalendarEmbed';
import * as S from './style';

/** The calendar block in the editor: which calendar and view it shows, and that calendar
 * as the page's readers will see it. */
export function CalendarBlock({ node, updateAttributes, selected }: NodeViewProps) {
  const { t } = useTranslation();
  const calendar = node.attrs.calendar as string | null;
  const view = (node.attrs.view as CalendarMode | null) ?? 'month';
  const options = useQuery({
    queryKey: calendarKeys.list(null),
    queryFn: () => fetchCalendars(),
    enabled: !calendar || selected,
  });

  return (
    <NodeViewWrapper data-folio="calendar" contentEditable={false}>
      {(!calendar || selected) && (
        <S.Picker>
          <CalendarDays aria-hidden />
          <Select
            aria-label={t('folio.calendar.block.choose')}
            value={calendar ?? ''}
            onChange={(e) => updateAttributes({ calendar: e.target.value || null })}
          >
            <option value="">{t('folio.calendar.block.choose')}</option>
            {options.data?.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name} · {c.space}
              </option>
            ))}
          </Select>
          <Select
            aria-label={t('folio.calendar.block.view')}
            value={view}
            onChange={(e) => updateAttributes({ view: e.target.value })}
          >
            <option value="month">{t('folio.calendar.show.month')}</option>
            <option value="week">{t('folio.calendar.show.week')}</option>
          </Select>
          {options.data?.length === 0 && <span>{t('folio.calendar.block.none')}</span>}
          {calendar && (
            <Button size="sm" variant="ghost" onClick={() => updateAttributes({ calendar: null })}>
              {t('common.remove')}
            </Button>
          )}
        </S.Picker>
      )}
      {calendar && <CalendarEmbed key={`${calendar}-${view}`} calendarId={calendar} view={view} />}
    </NodeViewWrapper>
  );
}
