'use client';

import { IKpiCard } from '../../lib/types/dashboard';
import KpiCard, { KpiCardSkeleton } from './KpiCard';
import { AlertCircle, RefreshCw } from 'lucide-react';

interface KpiCardGridProps {
  cards: IKpiCard[];
  loading: boolean;
  error: string | null;
  onRetry: () => void;
}

export default function KpiCardGrid({ cards, loading, error, onRetry }: KpiCardGridProps) {
  if (error) {
    return (
      <div className="flex items-center justify-center rounded-2xl bg-white p-8 shadow-sm">
        <div className="flex flex-col items-center gap-3 text-center">
          <AlertCircle size={40} className="text-red-400" />
          <p className="text-sm text-gray-600">{error}</p>
          <button
            onClick={onRetry}
            className="flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm text-white hover:bg-indigo-700 transition-colors"
          >
            <RefreshCw size={14} />
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <KpiCardSkeleton key={i} />
        ))}
      </div>
    );
  }

  if (cards.length === 0) {
    return (
      <div className="flex items-center justify-center rounded-2xl bg-white p-8 shadow-sm">
        <p className="text-sm text-gray-500">No KPI data available</p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {cards.map((card) => (
        <KpiCard key={card.id} data={card} />
      ))}
    </div>
  );
}
