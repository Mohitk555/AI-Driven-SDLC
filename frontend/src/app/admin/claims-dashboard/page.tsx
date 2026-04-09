'use client';

import { useEffect, useState } from 'react';
import { getClaimsDashboard } from '@/lib/api/policyApi';
import type { IClaimsDashboardResponse } from '@/lib/types/policy';

const CLAIM_TYPES = ['auto', 'health', 'property', 'life'] as const;

function StatCard({
  title,
  value,
  subtitle,
  color = 'primary',
}: {
  title: string;
  value: string;
  subtitle?: string;
  color?: 'primary' | 'green' | 'red' | 'amber' | 'gray';
}) {
  const colorMap = {
    primary: 'border-primary-200 bg-primary-50 text-primary-700',
    green: 'border-green-200 bg-green-50 text-green-700',
    red: 'border-red-200 bg-red-50 text-red-700',
    amber: 'border-amber-200 bg-amber-50 text-amber-700',
    gray: 'border-gray-200 bg-gray-50 text-gray-700',
  };
  return (
    <div className={`rounded-xl border p-5 ${colorMap[color]}`}>
      <p className="text-xs font-medium uppercase tracking-wider opacity-75">
        {title}
      </p>
      <p className="mt-1 text-3xl font-bold">{value}</p>
      {subtitle && <p className="mt-1 text-xs opacity-60">{subtitle}</p>}
    </div>
  );
}

export default function ClaimsDashboardPage() {
  const [data, setData] = useState<IClaimsDashboardResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [claimType, setClaimType] = useState('');

  function fetchData() {
    setLoading(true);
    setError('');
    getClaimsDashboard(
      dateFrom || undefined,
      dateTo || undefined,
      claimType || undefined,
    )
      .then(setData)
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    fetchData();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  function handleApplyFilters() {
    fetchData();
  }

  if (loading && !data) {
    return (
      <div className="flex justify-center py-20">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-200 border-t-primary-600" />
      </div>
    );
  }

  if (error && !data) {
    return (
      <div className="card text-center text-red-600">
        <p>Error loading dashboard: {error}</p>
      </div>
    );
  }

  if (!data) return null;

  const statusOrder = [
    'submitted',
    'under_review',
    'info_required',
    'approved',
    'rejected',
  ];
  const statusLabels: Record<string, string> = {
    submitted: 'Submitted',
    under_review: 'Under Review',
    info_required: 'Info Required',
    approved: 'Approved',
    rejected: 'Rejected',
  };

  return (
    <div>
      <h1 className="mb-6 text-2xl font-bold text-gray-900">
        Claims Dashboard
      </h1>

      {/* Filters */}
      <div className="mb-6 flex flex-wrap items-end gap-4 rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
        <div>
          <label className="block text-xs font-medium text-gray-500">
            From
          </label>
          <input
            type="date"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
            className="mt-1 rounded-lg border border-gray-300 px-3 py-2 text-sm"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-500">To</label>
          <input
            type="date"
            value={dateTo}
            onChange={(e) => setDateTo(e.target.value)}
            className="mt-1 rounded-lg border border-gray-300 px-3 py-2 text-sm"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-500">
            Claim Type
          </label>
          <select
            value={claimType}
            onChange={(e) => setClaimType(e.target.value)}
            className="mt-1 rounded-lg border border-gray-300 px-3 py-2 text-sm"
          >
            <option value="">All Types</option>
            {CLAIM_TYPES.map((t) => (
              <option key={t} value={t}>
                {t.charAt(0).toUpperCase() + t.slice(1)}
              </option>
            ))}
          </select>
        </div>
        <button
          onClick={handleApplyFilters}
          className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700"
        >
          {loading ? 'Loading...' : 'Apply'}
        </button>
      </div>

      {/* Stat Cards */}
      <div className="mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
        <StatCard
          title="Total Claims"
          value={data.totalClaims.toLocaleString()}
          color="primary"
        />
        <StatCard
          title="Approval Rate"
          value={
            data.approvalRate !== null ? `${data.approvalRate}%` : 'N/A'
          }
          subtitle={`${data.approvedCount} approved`}
          color="green"
        />
        <StatCard
          title="Rejection Rate"
          value={
            data.rejectionRate !== null ? `${data.rejectionRate}%` : 'N/A'
          }
          subtitle={`${data.rejectedCount} rejected`}
          color="red"
        />
        <StatCard
          title="Avg Processing"
          value={
            data.averageProcessingDays !== null
              ? `${data.averageProcessingDays} days`
              : 'N/A'
          }
          color="amber"
        />
        <StatCard
          title="Avg Claim Amount"
          value={
            data.averageAmount !== null
              ? `$${data.averageAmount.toLocaleString(undefined, {
                  minimumFractionDigits: 2,
                  maximumFractionDigits: 2,
                })}`
              : 'N/A'
          }
          subtitle={`$${data.totalAmount.toLocaleString(undefined, {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
          })} total`}
          color="gray"
        />
      </div>

      {/* Status Breakdown Table */}
      <div className="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
        <h2 className="border-b border-gray-200 bg-gray-50 px-6 py-3 text-sm font-semibold text-gray-700">
          Status Breakdown
        </h2>
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                Status
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">
                Count
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">
                Percentage
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {statusOrder.map((status) => {
              const count = data.countByStatus[status] ?? 0;
              const pct =
                data.totalClaims > 0
                  ? ((count / data.totalClaims) * 100).toFixed(1)
                  : '0.0';
              return (
                <tr key={status}>
                  <td className="px-6 py-3 text-sm font-medium text-gray-900">
                    {statusLabels[status] || status}
                  </td>
                  <td className="px-6 py-3 text-right text-sm text-gray-900">
                    {count}
                  </td>
                  <td className="px-6 py-3 text-right text-sm text-gray-500">
                    {pct}%
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {data.totalClaims === 0 && (
        <div className="mt-6 rounded-lg border border-gray-200 bg-gray-50 p-6 text-center text-gray-500">
          No claims found for the selected filters.
        </div>
      )}
    </div>
  );
}
