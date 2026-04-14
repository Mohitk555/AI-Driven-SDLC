'use client';

interface StatusBadgeProps {
  status: string;
}

const colorMap: Record<string, string> = {
  pending: 'bg-yellow-100 text-yellow-800',
  purchased: 'bg-green-100 text-green-800',
  expired: 'bg-gray-100 text-gray-600',
  active: 'bg-green-100 text-green-800',
  cancelled: 'bg-red-100 text-red-800',
  lapsed: 'bg-orange-100 text-orange-800',
  reinstated: 'bg-blue-100 text-blue-800',
};

export default function StatusBadge({ status }: StatusBadgeProps) {
  const colors = colorMap[status.toLowerCase()] || 'bg-gray-100 text-gray-700';

  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ${colors}`}
    >
      {status}
    </span>
  );
}
