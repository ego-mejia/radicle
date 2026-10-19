import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from '@tanstack/react-router';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '../../../../components/ui/Button';
import { Field, FormError } from '../../../../components/ui/Field';
import { Input, Textarea } from '../../../../components/ui/Input';
import { Modal } from '../../../../components/ui/Modal';
import { useErrorMessage } from '../../../../hooks/useErrorMessage';
import { authKeys } from '../../../../services/api/auth';
import { createProject, projectKeys } from '../../../../services/api/projects';
import * as S from './style';

type Props = { open: boolean; onOpenChange: (open: boolean) => void };

export function CreateProjectModal({ open, onOpenChange }: Props) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const errorMessage = useErrorMessage();
  const [form, setForm] = useState({ key: '', name: '', description_md: '' });
  const mutation = useMutation({
    mutationFn: () => createProject(form),
    onSuccess: async (project) => {
      await queryClient.invalidateQueries({ queryKey: projectKeys.all });
      await queryClient.invalidateQueries({ queryKey: authKeys.me });
      onOpenChange(false);
      setForm({ key: '', name: '', description_md: '' });
      await navigate({
        to: '/p/$key/settings',
        params: { key: project.key },
        search: { tab: 'areas' },
      });
    },
  });

  return (
    <Modal
      open={open}
      onOpenChange={onOpenChange}
      title={t('projects.create')}
      footer={
        <>
          <Button onClick={() => onOpenChange(false)}>{t('common.cancel')}</Button>
          <Button
            variant="primary"
            type="submit"
            form="create-project"
            disabled={mutation.isPending}
          >
            {t('common.create')}
          </Button>
        </>
      }
    >
      <S.Form
        id="create-project"
        onSubmit={(e) => {
          e.preventDefault();
          mutation.mutate();
        }}
      >
        <FormError>{mutation.error ? errorMessage(mutation.error) : null}</FormError>
        <Field label={t('projects.name')}>
          <Input
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            required
            autoFocus
          />
        </Field>
        <Field label={t('projects.key')} hint={t('projects.keyHint')}>
          <S.KeyInput
            value={form.key}
            onChange={(e) => setForm({ ...form, key: e.target.value.toUpperCase() })}
            required
            pattern="[A-Z][A-Z0-9]{1,9}"
            maxLength={10}
          />
        </Field>
        <Field label={`${t('projects.description')} (${t('common.optional')})`}>
          <Textarea
            value={form.description_md}
            onChange={(e) => setForm({ ...form, description_md: e.target.value })}
          />
        </Field>
      </S.Form>
    </Modal>
  );
}
