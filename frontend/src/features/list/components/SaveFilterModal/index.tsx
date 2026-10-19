import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '../../../../components/ui/Button';
import { Field, FormError } from '../../../../components/ui/Field';
import { Input, Select } from '../../../../components/ui/Input';
import { Modal } from '../../../../components/ui/Modal';
import { useErrorMessage } from '../../../../hooks/useErrorMessage';
import { useMe } from '../../../../hooks/useMe';
import { createFilter } from '../../../../services/api/work';

type Visibility = 'private' | 'project' | 'instance';
type Props = { project: string; rql: string; onClose: () => void };

/** Save the current query as a filter: private, for the project or for everyone. */
export function SaveFilterModal({ project, rql, onClose }: Props) {
  const { t } = useTranslation();
  const me = useMe();
  const queryClient = useQueryClient();
  const errorMessage = useErrorMessage();
  const [name, setName] = useState('');
  const [visibility, setVisibility] = useState<Visibility>('private');
  const save = useMutation({
    mutationFn: () => createFilter({ name, rql, visibility, project }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['filters'] });
      onClose();
    },
  });
  return (
    <Modal
      open
      onOpenChange={(open) => !open && onClose()}
      title={t('filters.save')}
      footer={
        <>
          <Button onClick={onClose}>{t('common.cancel')}</Button>
          <Button
            variant="primary"
            type="submit"
            form="save-filter"
            disabled={!name.trim() || save.isPending}
          >
            {t('common.save')}
          </Button>
        </>
      }
    >
      <form
        id="save-filter"
        style={{ display: 'contents' }}
        onSubmit={(e) => {
          e.preventDefault();
          save.mutate();
        }}
      >
        <FormError>{save.error ? errorMessage(save.error) : null}</FormError>
        <Field label={t('filters.name')}>
          <Input value={name} autoFocus onChange={(e) => setName(e.target.value)} />
        </Field>
        <Field label={t('filters.visibility')}>
          <Select value={visibility} onChange={(e) => setVisibility(e.target.value as Visibility)}>
            <option value="private">{t('filters.visibilities.private')}</option>
            <option value="project">{t('filters.visibilities.project', { key: project })}</option>
            {me.is_instance_admin && (
              <option value="instance">{t('filters.visibilities.instance')}</option>
            )}
          </Select>
        </Field>
        <Field label="RQL">
          <Input value={rql} readOnly />
        </Field>
      </form>
    </Modal>
  );
}
