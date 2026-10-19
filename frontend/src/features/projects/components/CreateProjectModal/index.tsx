import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from '@tanstack/react-router';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '../../../../components/ui/Button';
import { Field, FormError } from '../../../../components/ui/Field';
import { Input, Select, Textarea } from '../../../../components/ui/Input';
import { Modal } from '../../../../components/ui/Modal';
import { useErrorMessage } from '../../../../hooks/useErrorMessage';
import { authKeys } from '../../../../services/api/auth';
import { createProject, projectKeys } from '../../../../services/api/projects';
import { fetchTemplates, templateKeys } from '../../../../services/api/templates';
import { TemplatePreview } from './components/TemplatePreview';
import * as S from './style';

type Props = { open: boolean; onOpenChange: (open: boolean) => void };

export function CreateProjectModal({ open, onOpenChange }: Props) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const errorMessage = useErrorMessage();
  const [form, setForm] = useState({ key: '', name: '', description_md: '' });
  const [templateId, setTemplateId] = useState('');
  const [mode, setMode] = useState<'linked' | 'detached'>('linked');
  const { data: templates = [] } = useQuery({
    queryKey: templateKeys.list(false),
    queryFn: () => fetchTemplates(false),
    enabled: open,
  });
  const selected = templateId || templates.find((tpl) => tpl.is_default)?.id || '';
  const mutation = useMutation({
    mutationFn: () =>
      createProject({ ...form, template_id: selected || null, template_mode: mode }),
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
        <Field label={t('templates.template')}>
          <Select value={selected} onChange={(e) => setTemplateId(e.target.value)}>
            {templates.map((tpl) => (
              <option key={tpl.id} value={tpl.id}>
                {tpl.name}
              </option>
            ))}
          </Select>
        </Field>
        {selected && <TemplatePreview templateId={selected} />}
        <Field label={t('templates.mode')} group>
          <S.Modes>
            {(['linked', 'detached'] as const).map((value) => (
              <label key={value}>
                <input
                  type="radio"
                  name="template-mode"
                  checked={mode === value}
                  onChange={() => setMode(value)}
                />
                <span>
                  <strong>{t(`templates.modes.${value}`)}</strong>
                  <small>{t(`templates.modes.${value}Help`)}</small>
                </span>
              </label>
            ))}
          </S.Modes>
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
