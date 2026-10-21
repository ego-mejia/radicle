import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '../../../../components/ui/Button';
import { ConfirmDialog } from '../../../../components/ui/ConfirmDialog';
import { Field, FormError } from '../../../../components/ui/Field';
import { Input, Select } from '../../../../components/ui/Input';
import { Modal } from '../../../../components/ui/Modal';
import { useErrorMessage } from '../../../../hooks/useErrorMessage';
import {
  type CalendarColor,
  calendarKeys,
  createCalendar,
  deleteCalendar,
  feedUrl,
  type FolioCalendar,
  rotateFeed,
  updateCalendar,
} from '../../../../services/api/folioCalendars';
import * as S from './style';

const COLORS: CalendarColor[] = ['blue', 'green', 'purple', 'orange', 'red', 'teal', 'gray'];

type Props = {
  space: string;
  /** The calendar to change; without it, a new one. */
  calendar?: FolioCalendar | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSaved?: (calendar: FolioCalendar | null) => void;
};

/** A space admin creates a calendar or changes one: name, color, the Docket projects whose
 * milestones it shows, and its feed link, which can be replaced or the calendar deleted. */
export function CalendarSettingsDialog({ space, calendar, open, onOpenChange, onSaved }: Props) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const errorMessage = useErrorMessage();
  const [name, setName] = useState(calendar?.name ?? '');
  const [color, setColor] = useState<CalendarColor>(calendar?.color ?? 'blue');
  const [projects, setProjects] = useState(calendar?.docket_projects.join(', ') ?? '');
  const [confirming, setConfirming] = useState(false);
  const refresh = () => queryClient.invalidateQueries({ queryKey: calendarKeys.all });
  const keys = projects
    .split(/[\s,]+/)
    .map((k) => k.trim())
    .filter(Boolean);
  const save = useMutation({
    mutationFn: () => {
      const body = { name: name.trim(), color, docket_projects: keys };
      return calendar ? updateCalendar(calendar.id, body) : createCalendar({ space, ...body });
    },
    onSuccess: async (saved) => {
      await refresh();
      onSaved?.(saved);
      onOpenChange(false);
    },
  });
  const rotate = useMutation({
    mutationFn: () => rotateFeed(calendar?.id ?? ''),
    onSuccess: refresh,
  });
  const remove = useMutation({
    mutationFn: () => deleteCalendar(calendar?.id ?? ''),
    onSuccess: async () => {
      await refresh();
      onSaved?.(null);
      onOpenChange(false);
    },
  });
  const current = rotate.data ?? calendar;
  const error = save.error ?? rotate.error ?? remove.error;

  return (
    <Modal
      open={open}
      onOpenChange={onOpenChange}
      title={t(calendar ? 'folio.calendar.settings.title' : 'folio.calendar.settings.new')}
      footer={
        <>
          {calendar && (
            <Button variant="danger" onClick={() => setConfirming(true)}>
              {t('common.delete')}
            </Button>
          )}
          <S.Spacer />
          <Button onClick={() => onOpenChange(false)}>{t('common.cancel')}</Button>
          <Button
            variant="primary"
            type="submit"
            form="folio-calendar-settings"
            disabled={!name.trim() || save.isPending}
          >
            {t(calendar ? 'common.save' : 'common.create')}
          </Button>
        </>
      }
    >
      <S.Form
        id="folio-calendar-settings"
        onSubmit={(e) => {
          e.preventDefault();
          if (name.trim()) save.mutate();
        }}
      >
        <Field label={t('folio.calendar.settings.name')}>
          <Input
            value={name}
            onChange={(e) => setName(e.target.value)}
            maxLength={80}
            autoFocus
            required
          />
        </Field>
        <Field label={t('folio.calendar.settings.color')}>
          <Select value={color} onChange={(e) => setColor(e.target.value as CalendarColor)}>
            {COLORS.map((c) => (
              <option key={c} value={c}>
                {t(`folio.calendar.color.${c}`)}
              </option>
            ))}
          </Select>
        </Field>
        <Field
          label={t('folio.calendar.settings.projects')}
          hint={t('folio.calendar.settings.projectsHint')}
        >
          <Input value={projects} onChange={(e) => setProjects(e.target.value)} />
        </Field>
        {current && (
          <Field label={t('folio.calendar.feed.label')} hint={t('folio.calendar.feed.hint')}>
            <S.Feed>
              <Input
                readOnly
                value={feedUrl(current)}
                aria-label={t('folio.calendar.feed.label')}
              />
              <Button size="sm" onClick={() => rotate.mutate()} disabled={rotate.isPending}>
                {t('folio.calendar.feed.rotate')}
              </Button>
            </S.Feed>
          </Field>
        )}
        <FormError>{error ? errorMessage(error) : null}</FormError>
      </S.Form>
      <ConfirmDialog
        open={confirming}
        title={t('folio.calendar.settings.deleteTitle')}
        message={t('folio.calendar.settings.deleteMessage', { name: calendar?.name ?? '' })}
        confirmLabel={t('common.delete')}
        onConfirm={() => {
          setConfirming(false);
          remove.mutate();
        }}
        onCancel={() => setConfirming(false)}
      />
    </Modal>
  );
}
