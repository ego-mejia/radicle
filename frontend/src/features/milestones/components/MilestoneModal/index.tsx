import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '../../../../components/ui/Button';
import { Field, FormError } from '../../../../components/ui/Field';
import { Input, Textarea } from '../../../../components/ui/Input';
import { Modal } from '../../../../components/ui/Modal';
import { useErrorMessage } from '../../../../hooks/useErrorMessage';
import { createMilestone, patchMilestone, projectKeys } from '../../../../services/api/projects';
import type { Milestone } from '../../../../services/api/types';

type Props = { project: string; milestone?: Milestone; onClose: () => void };

/** Create a milestone, or edit one when `milestone` is given. */
export function MilestoneModal({ project, milestone, onClose }: Props) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const errorMessage = useErrorMessage();
  const [form, setForm] = useState({
    name: milestone?.name ?? '',
    target_date: milestone?.target_date ?? '',
    description_md: milestone?.description_md ?? '',
  });
  const mutation = useMutation({
    mutationFn: () => {
      const body = { ...form, target_date: form.target_date || null };
      return milestone
        ? patchMilestone(project, milestone.name, body)
        : createMilestone(project, body);
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: projectKeys.detail(project) });
      onClose();
    },
  });

  return (
    <Modal
      open
      onOpenChange={(open) => !open && onClose()}
      title={milestone ? t('milestones.edit') : t('milestones.create')}
      footer={
        <>
          <Button onClick={onClose}>{t('common.cancel')}</Button>
          <Button
            variant="primary"
            onClick={() => mutation.mutate()}
            disabled={!form.name.trim() || mutation.isPending}
          >
            {t('common.save')}
          </Button>
        </>
      }
    >
      <FormError>{mutation.error ? errorMessage(mutation.error) : null}</FormError>
      <Field label={t('milestones.name')}>
        <Input
          value={form.name}
          onChange={(e) => setForm({ ...form, name: e.target.value })}
          autoFocus
        />
      </Field>
      <Field label={t('milestones.targetDate')}>
        <Input
          type="date"
          value={form.target_date}
          onChange={(e) => setForm({ ...form, target_date: e.target.value })}
        />
      </Field>
      <Field label={`${t('projects.description')} (${t('common.optional')})`}>
        <Textarea
          value={form.description_md}
          onChange={(e) => setForm({ ...form, description_md: e.target.value })}
        />
      </Field>
    </Modal>
  );
}
