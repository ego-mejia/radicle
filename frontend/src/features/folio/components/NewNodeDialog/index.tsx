import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from '@tanstack/react-router';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '../../../../components/ui/Button';
import { Field } from '../../../../components/ui/Field';
import { Input } from '../../../../components/ui/Input';
import { Modal } from '../../../../components/ui/Modal';
import { useErrorMessage } from '../../../../hooks/useErrorMessage';
import { createNode, folioKeys } from '../../../../services/api/folio';
import * as S from './style';

export type NewKind = 'page' | 'folder' | 'blog_post';

type Props = {
  space: string;
  kind: NewKind;
  parent?: string | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
};

/** Name a new page, folder or post. Pages and posts open in the editor; folders stay. */
export function NewNodeDialog({ space, kind, parent = null, open, onOpenChange }: Props) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const errorMessage = useErrorMessage();
  const [title, setTitle] = useState('');
  const create = useMutation({
    mutationFn: () =>
      createNode({
        space,
        kind,
        title: title.trim(),
        parent: kind === 'blog_post' ? null : parent,
      }),
    onSuccess: async (node) => {
      await queryClient.invalidateQueries({ queryKey: folioKeys.space(space) });
      setTitle('');
      onOpenChange(false);
      if (kind !== 'folder') {
        await navigate({ to: '/folio/p/$page/edit', params: { page: `${node.id}-${node.slug}` } });
      }
    },
  });

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (title.trim()) create.mutate();
  };

  return (
    <Modal
      open={open}
      onOpenChange={onOpenChange}
      title={t(`folio.space.new.${kind}`)}
      footer={
        <>
          <Button onClick={() => onOpenChange(false)}>{t('common.cancel')}</Button>
          <Button
            variant="primary"
            type="submit"
            form="folio-new-node"
            disabled={!title.trim() || create.isPending}
          >
            {t('common.create')}
          </Button>
        </>
      }
    >
      <S.Form id="folio-new-node" onSubmit={submit}>
        <Field
          label={t('folio.space.new.title')}
          error={create.error ? errorMessage(create.error) : null}
        >
          <Input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            maxLength={200}
            autoFocus
            required
          />
        </Field>
      </S.Form>
    </Modal>
  );
}
