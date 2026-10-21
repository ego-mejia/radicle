import { useQuery } from '@tanstack/react-query';
import { FolderPlus } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '../../../../../../components/ui/Button';
import { fetchFolioMe, folioKeys } from '../../../../../../services/api/folio';
import { NewSpaceDialog } from '../../../../components/NewSpaceDialog';

/** "New space", for Folio creators and admins. */
export function NewSpaceButton() {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const { data: me } = useQuery({ queryKey: folioKeys.me, queryFn: fetchFolioMe });
  if (me?.role !== 'creator' && me?.role !== 'admin') return null;
  return (
    <>
      <Button onClick={() => setOpen(true)}>
        <FolderPlus aria-hidden />
        {t('folio.newSpace.button')}
      </Button>
      <NewSpaceDialog open={open} onOpenChange={setOpen} />
    </>
  );
}
