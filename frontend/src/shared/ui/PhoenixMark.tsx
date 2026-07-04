/** Феникс ARKAND — фирменная графика брендовой панели. Пути не менять. */
export const PhoenixMark = ({ className }: { className?: string }) => (
  <svg
    className={className}
    viewBox="0 0 320 250"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    aria-hidden="true"
  >
    <defs>
      <linearGradient id="ph" x1="34" y1="200" x2="260" y2="30" gradientUnits="userSpaceOnUse">
        <stop offset="0" stopColor="#5E1214" />
        <stop offset=".5" stopColor="#921418" />
        <stop offset="1" stopColor="#C1474B" />
      </linearGradient>
      <linearGradient id="ph2" x1="60" y1="200" x2="280" y2="60" gradientUnits="userSpaceOnUse">
        <stop offset="0" stopColor="#7A1417" />
        <stop offset="1" stopColor="#AE3438" />
      </linearGradient>
    </defs>
    <path fill="url(#ph)" d="M152.9 157.5 Q168.6 95.1 159.8 29.2 Q161.0 94.0 131.1 154.5 Z" />
    <path fill="url(#ph)" d="M159.3 157.1 Q193.3 99.3 193.1 29.0 Q185.4 96.4 136.7 148.9 Z" />
    <path fill="url(#ph)" d="M164.2 156.4 Q210.1 109.6 221.8 41.4 Q203.0 105.2 143.8 143.6 Z" />
    <path fill="url(#ph)" d="M168.0 154.5 Q219.8 120.7 241.8 59.2 Q214.2 115.5 152.0 139.5 Z" />
    <path fill="url(#ph)" d="M172.0 152.0 Q223.3 130.3 252.3 79.0 Q219.1 124.7 160.0 136.0 Z" />
    <path fill="url(#ph2)" d="M171.4 154.3 Q213.6 98.6 279.3 101.0 Q211.2 92.8 164.6 137.7 Z" />
    <path fill="url(#ph)" d="M146.4 137.5 Q98.2 187.2 34.6 183.1 Q100.7 195.9 153.6 162.5 Z" />
    <path fill="url(#ph2)" d="M141.0 147.3 Q115.0 188.3 71.5 199.0 Q118.5 194.4 151.0 164.7 Z" />
  </svg>
);
