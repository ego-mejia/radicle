import { useMutation } from '@tanstack/react-query';
import { useNavigate } from '@tanstack/react-router';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '../../../../components/ui/Button';
import { Field, FormError } from '../../../../components/ui/Field';
import { Input } from '../../../../components/ui/Input';
import { Modal } from '../../../../components/ui/Modal';
import { useErrorMessage } from '../../../../hooks/useErrorMessage';
import { saveAsTemplate } from '../../../../services/api/templates';
import type { ProjectDetail } from '../../../../services/api/types';

/** Button + dialog: copy this project's configuration into a new template. */
export function SaveAsTemplate({ project }: { project: ProjectDetail }) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const errorMessage = useErrorMessage();
  const [open, setOpen] = useState(false);
  const [name, setName] = useState(project.name);
  const save = useMutation({
    mutationFn: () => saveAsTemplate(project.key, { name }),
    onSuccess: (template) =>
      void navigate({ to: '/admin/templates/$id', params: { id: template.id }, search: {} }),
  });
  return (
    <>
      <Button onClick={() => setOpen(true)}>{t('templates.saveAs')}</Button>
      <Modal
        open={open}
        onOpenChange={setOpen}
        title={t('templates.saveAs')}
        footer={
          <>
            <Button onClick={() => setOpen(false)}>{t('common.cancel')}</Button>
            <Button
              variant="primary"
              disabled={!name.trim() || save.isPending}
              onClick={() => save.mutate()}
            >
              {t('common.create')}
            </Button>
          </>
        }
      >
        <p>{t('templates.saveAsHelp')}</p>
        <FormError>{save.error ? errorMessage(save.error) : null}</FormError>
        <Field label={t('fields.name')}>
          <Input value={name} autoFocus onChange={(e) => setName(e.target.value)} />
        </Field>
      </Modal>
    </>
  );
}
