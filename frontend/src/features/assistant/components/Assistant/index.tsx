import { useState } from 'react';
import { Radi, type RadiMood } from '../Radi';
import { RadiChat } from '../RadiChat';

/** Radi and, when he is clicked, the help chat. Lives once in the app shell. */
export function Assistant() {
  const [open, setOpen] = useState(false);
  const [mood, setMood] = useState<RadiMood>('idle');
  return (
    <>
      {open && <RadiChat onClose={() => setOpen(false)} onMood={setMood} />}
      <Radi open={open} mood={open ? mood : 'idle'} onClick={() => setOpen(!open)} />
    </>
  );
}
