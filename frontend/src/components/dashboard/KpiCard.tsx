'use client';

import { DollarSign, ShoppingCart, Users, TrendingUp, ArrowUp, ArrowDown } from 'lucide-react';
import { Area, AreaChart, ResponsiveContainer } from 'recharts';
import { IKpiCard } from '../../lib/types/dashboard';

const iconMap = {
  dollar: DollarSign,
  cart: ShoppingCart,
  users: Users,
  trending: TrendingUp,
};

const iconBgMap = {
  dollar: 'bg-indigo-100 text-indigo-600',
  cart: 'bg-orange-100 text-orange-600',
  users: 'bg-green-100 text-green-600',
  trending: 'bg-blue-100 text-blue-600',
};

interface KpiCardProps {
  data: IKpiCard;
}

export default function KpiCard({ data }: KpiCardProps) {
  const Icon = iconMap[data.icon];
  const isPositive = data.change >= 0;
  const sparkData = data.sparklineData.map((v, i) => ({ index: i, value: v }));

  return (
    <div className="flex flex-col justify-between rounded-2xl bg-white p-5 shadow-sm" style={{ minHeight: 205 }}>
      <div className="flex items-start justify-between">
        <div>
          <div className={`mb-3 flex h-11 w-11 items-center justify-center rounded-xl ${iconBgMap[data.icon]}`}>
            <Icon size={22} />
          </div>
          <p className="text-sm font-medium text-[#667085]">{data.label}</p>
          <p className="mt-1 text-2xl font-bold text-[#061B2B]">{data.value}</p>
        </div>
        <div className="h-[49px] w-[105px]">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={sparkData}>
              <defs>
                <linearGradient id={`gradient-${data.id}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={isPositive ? '#22C55E' : '#EF4444'} stopOpacity={0.3} />
                  <stop offset="100%" stopColor={isPositive ? '#22C55E' : '#EF4444'} stopOpacity={0} />
                </linearGradient>
              </defs>
              <Area
                type="monotone"
                dataKey="value"
                stroke={isPositive ? '#22C55E' : '#EF4444'}
                strokeWidth={2}
                fill={`url(#gradient-${data.id})`}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>
      <div className="mt-3 flex items-center gap-1.5">
        <span
          className={`flex items-center gap-0.5 text-sm font-semibold ${
            isPositive ? 'text-green-500' : 'text-red-500'
          }`}
        >
          {isPositive ? <ArrowUp size={14} /> : <ArrowDown size={14} />}
          {Math.abs(data.change)}%
        </span>
        <span className="text-xs text-gray-400">{data.changeLabel}</span>
      </div>
    </div>
  );
}

export function KpiCardSkeleton() {
  return (
    <div className="animate-pulse rounded-2xl bg-white p-5 shadow-sm" style={{ minHeight: 205 }}>
      <div className="flex items-start justify-between">
        <div>
          <div className="mb-3 h-11 w-11 rounded-xl bg-gray-200" />
          <div className="h-4 w-20 rounded bg-gray-200" />
          <div className="mt-2 h-7 w-28 rounded bg-gray-200" />
        </div>
        <div className="h-[49px] w-[105px] rounded bg-gray-100" />
      </div>
      <div className="mt-3 h-4 w-32 rounded bg-gray-200" />
    </div>
  );
}
