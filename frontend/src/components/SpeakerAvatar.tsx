import { cn } from '@/lib/utils';

const AVATAR_COLORS = [
  'bg-blue-500',
  'bg-emerald-500',
  'bg-amber-500',
  'bg-rose-500',
  'bg-purple-500',
  'bg-cyan-500',
  'bg-orange-500',
  'bg-teal-500',
];

function hashName(name: string): number {
  let hash = 0;
  for (const ch of name) hash = (hash * 31 + ch.charCodeAt(0)) | 0;
  return Math.abs(hash) % AVATAR_COLORS.length;
}

function getInitials(name: string): string {
  const parts = name.trim().split(/\s+/);
  if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase();
  return (name[0] ?? '?').toUpperCase();
}

interface Props {
  name: string;
  size?: number;
}

export default function SpeakerAvatar({ name, size = 32 }: Props) {
  const colorClass = AVATAR_COLORS[hashName(name)];
  return (
    <div
      className={cn(colorClass, 'rounded-full flex items-center justify-center text-white font-semibold shrink-0')}
      style={{ width: size, height: size, fontSize: size * 0.375 }}
    >
      {getInitials(name)}
    </div>
  );
}
