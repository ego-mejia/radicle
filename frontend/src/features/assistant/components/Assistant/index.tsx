import { useState } from 'react';
import { Radi } from '../Radi';

/** Radi and, when he is clicked, the help chat. Lives once in the app shell. */
export function Assistant() {
  const [open, setOpen] = useState(false);
  return <Radi open={open} mood={open ? 'listening' : 'idle'} onClick={() => setOpen(!open)} />;
}
