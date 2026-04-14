'use client';

import { useState, useEffect } from 'react';
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { ISalesDataPoint, DateRange } from '../../lib/types/dashboard';
import { fetchSalesActivityByRange } from '../../lib/mock/dashboardData';
import { AlertCircle, RefreshCw } from 'lucide-react';

interface SalesActivityChartProps {
  initialData: ISalesDataPoint[];
}

export default function SalesActivityChart({ initialData }: SalesActivityChartProps) {
  const [range, setRange] = useState<DateRange>('monthly');
  const [data, setData] = useState<ISalesDataPoint[]>(initialData);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    fetchSalesActivityByRange(range)
      .then(setData)
      .catch(() => setError('Failed to load sales activity data'))
      .finally(() => setLoading(false));
  }, [range]);

  return (
    <div className="flex flex-col rounded-2xl bg-white p-6 shadow-sm" style={{ minHeight: 435 }}>
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-[#061B2B]">General Sale</h3>
        <div className="flex items-center gap-3">
          <div className="flex rounded-lg bg-gray-100 p-1">
            {(['weekly', 'monthly', 'yearly'] as DateRange[]).map((r) => (
              <button
                key={r}
                onClick={() => setRange(r)}
                className={`rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
                  range === r
                    ? 'bg-white text-indigo-600 shadow-sm'
                    : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                {r.charAt(0).toUpperCase() + r.slice(1)}
              </button>
            ))}
          </div>
          <button className="text-sm font-medium text-indigo-600 hover:text-indigo-700">
            View Report
          </button>
        </div>
      </div>

      <div className="my-4 h-px bg-gray-100" />

      <div className="flex items-center gap-6 text-sm">
        <div>
          <span className="text-gray-500">Total Revenue</span>
          <span className="ml-2 text-lg font-bold text-[#061B2B]">$75,500</span>
        </div>
        <div>
          <span className="text-gray-500">Total Sales</span>
          <span className="ml-2 text-lg font-bold text-[#061B2B]">1,250</span>
        </div>
      </div>

      <div className="mt-4 flex-1">
        {error ? (
          <div className="flex h-full items-center justify-center">
            <div className="flex flex-col items-center gap-2">
              <AlertCircle size={32} className="text-red-400" />
              <p className="text-sm text-gray-500">{error}</p>
              <button
                onClick={() => setRange(range)}
                className="flex items-center gap-1 text-sm text-indigo-600 hover:text-indigo-700"
              >
                <RefreshCw size={14} /> Retry
              </button>
            </div>
          </div>
        ) : loading ? (
          <div className="flex h-full items-center justify-center">
            <div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-200 border-t-indigo-600" />
          </div>
        ) : data.length === 0 ? (
          <div className="flex h-full items-center justify-center">
            <p className="text-sm text-gray-400">No sales data for this period</p>
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={248}>
            <AreaChart data={data}>
              <defs>
                <linearGradient id="salesGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#4F46E5" stopOpacity={0.2} />
                  <stop offset="100%" stopColor="#4F46E5" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#F0F0F0" vertical={false} />
              <XAxis dataKey="date" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#667085' }} />
              <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#667085' }} />
              <Tooltip
                contentStyle={{
                  borderRadius: 8,
                  border: 'none',
                  boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
                  fontSize: 13,
                }}
              />
              <Area
                type="monotone"
                dataKey="amount"
                stroke="#4F46E5"
                strokeWidth={2.5}
                fill="url(#salesGradient)"
              />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
