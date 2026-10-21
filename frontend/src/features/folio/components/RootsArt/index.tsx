/** Radicle's roots, drawn in the accent color over the dark cover. */
export function RootsArt() {
  return (
    <svg viewBox="0 0 720 260" preserveAspectRatio="xMidYMid slice" aria-hidden>
      <g fill="none" stroke="currentColor" strokeLinecap="round">
        <path d="M360 40 C360 110 300 130 250 170 S170 240 120 260" strokeWidth="2.5" />
        <path d="M360 40 C365 120 420 140 470 175 S560 230 620 260" strokeWidth="2" opacity="0.7" />
        <path d="M300 125 C290 170 300 210 330 260" strokeWidth="1.5" opacity="0.5" />
        <path d="M430 140 C470 120 520 120 560 140" strokeWidth="1.5" opacity="0.5" />
      </g>
      <g fill="currentColor">
        <ellipse cx="360" cy="34" rx="26" ry="20" />
        <circle cx="250" cy="170" r="5" />
        <circle cx="470" cy="175" r="5" />
        <circle cx="560" cy="140" r="4" />
      </g>
    </svg>
  );
}
