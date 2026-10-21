import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from '@tanstack/react-router';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '../../../../components/ui/Button';
import { Field, FormError } from '../../../../components/ui/Field';
import { Input } from '../../../../components/ui/Input';
import { Modal } from '../../../../components/ui/Modal';
import { useErrorMessage } from '../../../../hooks/useErrorMessage';
import { createSpace, createSpaceFromTemplate, folioKeys } from '../../../../services/api/folio';
import { TemplatePicker } from '../TemplatePicker';
import { keyFor } from './keyFor';
import * as S from './style';

type Props = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
};

/** Name a new space, empty or from a space template (Folio 3.1), then open it. */
export function NewSpaceDialog({ open, onOpenChange }: Props) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const errorMessage = useErrorMessage();
  const [name, setName] = useState('');
  const [typedKey, setTypedKey] = useState<string | null>(null);
  const [template, setTemplate] = useState<string | null>(null);
  const key = typedKey ?? keyFor(name);
  const create = useMutation({
    mutationFn: () => {
      const body = { key, name: name.trim() };
      return template ? createSpaceFromTemplate({ ...body, template }) : createSpace(body);
    },
    onSuccess: async (space) => {
      await queryClient.invalidateQueries({ queryKey: folioKeys.spaces });
      setName('');
      setTypedKey(null);
      setTemplate(null);
      onOpenChange(false);
      await navigate({ to: '/folio/s/$key', params: { key: space.key } });
    },
  });
  const ready = name.trim() !== '' && key.length >= 2;

  return (
    <Modal
      open={open}
      onOpenChange={onOpenChange}
      title={t('folio.newSpace.title')}
      width={760}
      footer={
        <>
          <Button onClick={() => onOpenChange(false)}>{t('common.cancel')}</Button>
          <Button
            variant="primary"
            type="submit"
            form="folio-new-space"
            disabled={!ready || create.isPending}
          >
            {t('common.create')}
          </Button>
        </>
      }
    >
      <S.Form
        id="folio-new-space"
        onSubmit={(e) => {
          e.preventDefault();
          if (ready) create.mutate();
        }}
      >
        <S.Row>
          <Field label={t('folio.newSpace.name')}>
            <Input
              value={name}
              onChange={(e) => setName(e.target.value)}
              maxLength={120}
              autoFocus
              required
            />
          </Field>
          <Field label={t('folio.newSpace.key')} hint={t('folio.newSpace.keyHint')}>
            <Input
              value={key}
              onChange={(e) => setTypedKey(e.target.value.toLowerCase())}
              maxLength={40}
              pattern="[a-z0-9-]{2,40}"
              required
            />
          </Field>
        </S.Row>
        <TemplatePicker kind="space" value={template} onChange={setTemplate} />
        <FormError>{create.error ? errorMessage(create.error) : null}</FormError>
      </S.Form>
    </Modal>
  );
}
