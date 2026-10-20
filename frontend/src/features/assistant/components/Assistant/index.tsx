import { useState } from 'react';
import type { TourStep } from '../../lib/tour';
import { Radi, type RadiMood } from '../Radi';
import { type ChatLine, RadiChat } from '../RadiChat';
import { TourPlayer } from '../TourPlayer';

/** Radi, the help chat and his tours. Lives once in the app shell. */
export function Assistant() {
  const [open, setOpen] = useState(false);
  const [mood, setMood] = useState<RadiMood>('idle');
  const [lines, setLines] = useState<ChatLine[]>([]);
  const [tour, setTour] = useState<TourStep[] | null>(null);
  return (
    <>
      {open && !tour && (
        <RadiChat
          lines={lines}
          setLines={setLines}
          onClose={() => setOpen(false)}
          onMood={setMood}
          onTour={setTour}
        />
      )}
      {tour && (
        <TourPlayer
          steps={tour}
          onDone={() => {
            setTour(null);
            setOpen(true);
            setMood('answered');
          }}
        />
      )}
      <Radi
        open={open}
        mood={tour ? 'listening' : open ? mood : 'idle'}
        onClick={() => {
          setTour(null);
          setOpen(!open);
        }}
      />
    </>
  );
}
