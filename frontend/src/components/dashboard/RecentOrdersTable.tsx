'use client';

import { IRecentOrder } from '../../lib/types/dashboard';
import { ChevronRight, AlertCircle, RefreshCw } from 'lucide-react';

interface RecentOrdersTableProps {
  orders: IRecentOrder[];
  loading: boolean;
  error: string | null;
  onRetry: () => void;
}

const statusStyles: Record<IRecentOrder['status'], string> = {
  PAID: 'bg-green-100 text-green-700',
  PENDING: 'bg-yellow-100 text-yellow-700',
  CANCELLED: 'bg-red-100 text-red-700',
  REFUNDED: 'bg-gray-100 text-gray-700',
};

export default function RecentOrdersTable({ orders, loading, error, onRetry }: RecentOrdersTableProps) {
  return (
    <div className="rounded-2xl bg-white p-6 shadow-sm">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-[#061B2B]">Recent Orders</h3>
        <button className="flex items-center gap-1 rounded-lg border border-gray-200 px-4 py-2 text-sm font-medium text-gray-600 hover:bg-gray-50 transition-colors">
          View All
          <ChevronRight size={16} />
        </button>
      </div>

      <div className="mt-4">
        {error ? (
          <div className="flex flex-col items-center gap-3 py-8">
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
        ) : loading ? (
          <div className="space-y-3">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="flex animate-pulse items-center gap-4 rounded-lg p-3">
                <div className="h-4 w-16 rounded bg-gray-200" />
                <div className="h-4 w-40 rounded bg-gray-200" />
                <div className="h-4 w-12 rounded bg-gray-200" />
                <div className="h-4 w-24 rounded bg-gray-200" />
                <div className="h-4 w-16 rounded bg-gray-200" />
                <div className="h-6 w-20 rounded-full bg-gray-200" />
                <div className="ml-auto h-8 w-20 rounded bg-gray-200" />
              </div>
            ))}
          </div>
        ) : orders.length === 0 ? (
          <div className="flex flex-col items-center py-8">
            <p className="text-sm text-gray-400">No recent orders</p>
          </div>
        ) : (
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-100 text-left text-xs font-medium uppercase tracking-wider text-gray-400">
                <th className="pb-3 pr-4">ID</th>
                <th className="pb-3 pr-4">Item</th>
                <th className="pb-3 pr-4">Qty</th>
                <th className="pb-3 pr-4">Order Date</th>
                <th className="pb-3 pr-4">Amount</th>
                <th className="pb-3 pr-4">Status</th>
                <th className="pb-3" />
              </tr>
            </thead>
            <tbody>
              {orders.map((order) => (
                <tr key={order.id} className="border-b border-gray-50 last:border-0">
                  <td className="py-3.5 pr-4 text-sm font-semibold text-[#061B2B]">{order.id}</td>
                  <td className="py-3.5 pr-4 text-sm text-gray-600">{order.item}</td>
                  <td className="py-3.5 pr-4 text-sm text-gray-600">{order.quantity}</td>
                  <td className="py-3.5 pr-4 text-sm text-gray-600">{order.orderDate}</td>
                  <td className="py-3.5 pr-4 text-sm font-semibold text-[#061B2B]">
                    ${order.amount.toFixed(2)}
                  </td>
                  <td className="py-3.5 pr-4">
                    <span
                      className={`inline-flex rounded-full px-2.5 py-1 text-xs font-medium ${
                        statusStyles[order.status]
                      }`}
                    >
                      {order.status}
                    </span>
                  </td>
                  <td className="py-3.5">
                    <button className="rounded-lg border border-gray-200 px-3 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-50 transition-colors">
                      Details
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
