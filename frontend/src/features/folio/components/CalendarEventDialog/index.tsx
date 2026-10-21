import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '../../../../components/ui/Button';
import { ConfirmDialog } from '../../../../components/ui/ConfirmDialog';
import { Field, FormError } from '../../../../components/ui/Field';
import { Input, Select, Textarea } from '../../../../components/ui/Input';
import { Modal } from '../../../../components/ui/Modal';
import { useErrorMessage } from '../../../../hooks/useErrorMessage';
import {
  type CalendarEvent,
  calendarKeys,
  createEvent,
  deleteEvent,
  type EventCategory,
  updateEvent,
} from '../../../../services/api/folioCalendars';
import { blankForm, bodyOf, type EventForm, formOf, toggleAllDay } from '../../calendar/form';
import * as S from './style';

const CATEGORIES: EventCategory[] = ['event', 'release', 'vacation', 'oncall', 'other'];

type Props = {
  calendarId: string;
  /** The event to change; without it, a new one. */
  event?: CalendarEvent | null;
  /** The day a new event starts on. */
  day?: Date;
  open: boolean;
  onOpenChange: (open: boolean) => void;
};

/** Add an event to a calendar, or change or delete one you may edit. */
export function CalendarEventDialog({ calendarId, event, day, open, onOpenChange }: Props) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const errorMessage = useErrorMessage();
  const [form, setForm] = useState<EventForm>(() => (event ? formOf(event) : blankForm(day)));
  const [confirming, setConfirming] = useState(false);
  const readOnly = !!event && !event.can_edit;
  const done = async () => {
    await queryClient.invalidateQueries({ queryKey: calendarKeys.calendar(calendarId) });
    onOpenChange(false);
  };
  const save = useMutation({
    mutationFn: () =>
      event
        ? updateEvent(calendarId, event.id, bodyOf(form))
        : createEvent(calendarId, bodyOf(form)),
    onSuccess: done,
  });
  const remove = useMutation({
    mutationFn: () => deleteEvent(calendarId, event?.id ?? ''),
    onSuccess: done,
  });
  const set = (patch: Partial<EventForm>) => setForm((f) => ({ ...f, ...patch }));
  const kind = form.allDay ? 'date' : 'datetime-local';

  return (
    <Modal
      open={open}
      onOpenChange={onOpenChange}
      title={t(event ? 'folio.calendar.event.edit' : 'folio.calendar.event.new')}
      footer={
        readOnly ? (
          <Button onClick={() => onOpenChange(false)}>{t('common.close')}</Button>
        ) : (
          <>
            {event && (
              <Button variant="danger" onClick={() => setConfirming(true)}>
                {t('common.delete')}
              </Button>
            )}
            <S.Spacer />
            <Button onClick={() => onOpenChange(false)}>{t('common.cancel')}</Button>
            <Button
              variant="primary"
              type="submit"
              form="folio-calendar-event"
              disabled={!form.title.trim() || save.isPending}
            >
              {t(event ? 'common.save' : 'common.create')}
            </Button>
          </>
        )
      }
    >
      <S.Form
        id="folio-calendar-event"
        onSubmit={(e) => {
          e.preventDefault();
          if (form.title.trim()) save.mutate();
        }}
      >
        <S.Fieldset disabled={readOnly}>
          <Field label={t('folio.calendar.event.title')}>
            <Input
              value={form.title}
              onChange={(e) => set({ title: e.target.value })}
              maxLength={200}
              autoFocus
              required
            />
          </Field>
          <S.Check>
            <input
              type="checkbox"
              checked={form.allDay}
              onChange={(e) => setForm((f) => toggleAllDay(f, e.target.checked))}
            />
            {t('folio.calendar.event.allDay')}
          </S.Check>
          <S.Row>
            <Field label={t('folio.calendar.event.start')}>
              <Input
                type={kind}
                value={form.start}
                onChange={(e) => set({ start: e.target.value })}
                required
              />
            </Field>
            <Field
              label={t(form.allDay ? 'folio.calendar.event.lastDay' : 'folio.calendar.event.end')}
            >
              <Input
                type={kind}
                value={form.end}
                onChange={(e) => set({ end: e.target.value })}
                required
              />
            </Field>
          </S.Row>
          <S.Row>
            <Field label={t('folio.calendar.event.category')}>
              <Select
                value={form.category}
                onChange={(e) => set({ category: e.target.value as EventCategory })}
              >
                {CATEGORIES.map((c) => (
                  <option key={c} value={c}>
                    {t(`folio.calendar.category.${c}`)}
                  </option>
                ))}
              </Select>
            </Field>
            <Field
              label={t('folio.calendar.event.people')}
              hint={t('folio.calendar.event.peopleHint')}
            >
              <Input value={form.people} onChange={(e) => set({ people: e.target.value })} />
            </Field>
          </S.Row>
          <Field label={t('folio.calendar.event.description')}>
            <Textarea
              rows={3}
              value={form.description}
              onChange={(e) => set({ description: e.target.value })}
              maxLength={5000}
            />
          </Field>
          {event?.created_by && (
            <span>{t('folio.calendar.event.addedBy', { handle: event.created_by })}</span>
          )}
        </S.Fieldset>
        <FormError>
          {save.isError
            ? errorMessage(save.error)
            : remove.isError
              ? errorMessage(remove.error)
              : null}
        </FormError>
      </S.Form>
      <ConfirmDialog
        open={confirming}
        title={t('folio.calendar.event.deleteTitle')}
        message={t('folio.calendar.event.deleteMessage', { title: event?.title ?? '' })}
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
