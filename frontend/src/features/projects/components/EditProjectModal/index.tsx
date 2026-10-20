import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '../../../../components/ui/Button';
import { Field, FormError } from '../../../../components/ui/Field';
import { Input, Textarea } from '../../../../components/ui/Input';
import { Modal } from '../../../../components/ui/Modal';
import { useErrorMessage } from '../../../../hooks/useErrorMessage';
import { useToast } from '../../../../hooks/useToast';
import { patchProject, projectKeys } from '../../../../services/api/projects';
import { useProject } from '../../hooks/useProject';
import * as S from './style';

type Props = { projectKey: string; onClose: () => void };

function EditForm({
  projectKey,
  name: initialName,
  description: initialDescription,
  onClose,
}: Props & { name: string; description: string }) {
  const { t } = useTranslation();
  const toast = useToast();
  const errorMessage = useErrorMessage();
  const queryClient = useQueryClient();
  const [name, setName] = useState(initialName);
  const [description, setDescription] = useState(initialDescription);
  const save = useMutation({
    mutationFn: () => patchProject(projectKey, { name: name.trim(), description_md: description }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: projectKeys.all });
      toast(t('projects.saved', { key: projectKey }));
      onClose();
    },
  });
  return (
    <Modal
      open
      onOpenChange={(open) => !open && onClose()}
      title={t('projects.editTitle', { key: projectKey })}
      footer={
        <>
          <Button onClick={onClose}>{t('common.cancel')}</Button>
          <Button
            variant="primary"
            type="submit"
            form="edit-project"
            disabled={save.isPending || !name.trim()}
          >
            {t('common.save')}
          </Button>
        </>
      }
    >
      <S.Form
        id="edit-project"
        onSubmit={(e) => {
          e.preventDefault();
          save.mutate();
        }}
      >
        <Field label={t('projects.name')}>
          <Input value={name} onChange={(e) => setName(e.target.value)} required autoFocus />
        </Field>
        <Field label={t('projects.key')} hint={t('projects.keyFixed')}>
          <Input value={projectKey} disabled />
        </Field>
        <Field label={t('projects.description')}>
          <Textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={5} />
        </Field>
        <FormError>{save.error ? errorMessage(save.error) : null}</FormError>
      </S.Form>
    </Modal>
  );
}

/** Rename a project or change its description. The key never changes. */
export function EditProjectModal({ projectKey, onClose }: Props) {
  const { data: project } = useProject(projectKey);
  if (!project) return null;
  return (
    <EditForm
      projectKey={projectKey}
      name={project.name}
      description={project.description_md ?? ''}
      onClose={onClose}
    />
  );
}
