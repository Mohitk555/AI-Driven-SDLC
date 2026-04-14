'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { getPolicies, getExpiringPolicies } from '@/lib/api/policyApi';
import type {
  IPolicySummary,
  IPaginatedResponse,
  IExpiringPolicyItem,
} from '@/lib/types/policy';
import StatusBadge from '@/components/shared/StatusBadge';
import Pagination from '@/components/shared/Pagination';
import ExpiryBanner from '@/components/shared/ExpiryBanner';

export default function PoliciesListPage() {
  const [data, setData] = useState<IPaginatedResponse<IPolicySummary> | null>(
    null
  );
  const [expiringPolicies, setExpiringPolicies] = useState<IExpiringPolicyItem[]>([]);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    getExpiringPolicies()
      .then((resp) => setExpiringPolicies(resp.items))
      .catch(() => {});
  }, []);

  useEffect(() => {
    setLoading(true);
    setError('');
    getPolicies(page)
      .then(setData)
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, [page]);

  if (loading) {
    return (
      <div className="flex justify-center py-20">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-200 border-t-primary-600" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="card text-center text-red-600">
        <p>Error loading policies: {error}</p>
      </div>
    );
  }

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">My Policies</h1>
        <Link href="/quotes/new" className="btn-primary">
          Get New Quote
        </Link>
      </div>

      <ExpiryBanner policies={expiringPolicies} />

      {!data || data.items.length === 0 ? (
        <div className="card text-center text-gray-500">
          <p>No policies yet.</p>
          <Link
            href="/quotes/new"
            className="mt-2 inline-block text-primary-600 hover:underline"
          >
            Get a quote to start
          </Link>
        </div>
      ) : (
        <>
          <div className="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                    Policy #
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                    Vehicle
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                    Coverage
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                    Premium
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                    Status
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                    Effective
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                    Expires
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {data.items.map((policy) => (
                  <tr key={policy.id}>
                    <td className="px-6 py-4 text-sm font-medium text-primary-600">
                      <Link href={`/policies/${policy.id}`} className="hover:underline">
                        {policy.policyNumber}
                      </Link>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-900">
                      {policy.vehicleSummary}
                    </td>
                    <td className="px-6 py-4 text-sm capitalize text-gray-600">
                      {policy.coverageType}
                    </td>
                    <td className="px-6 py-4 text-sm font-semibold text-gray-900">
                      ${policy.premiumAmount.toFixed(2)}
                    </td>
                    <td className="px-6 py-4">
                      <StatusBadge status={policy.status} />
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-500">
                      {new Date(policy.effectiveDate).toLocaleDateString()}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-500">
                      {new Date(policy.expirationDate).toLocaleDateString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <Pagination
            page={data.page}
            total={data.total}
            pageSize={data.pageSize}
            onPageChange={setPage}
          />
        </>
      )}
    </div>
  );
}
