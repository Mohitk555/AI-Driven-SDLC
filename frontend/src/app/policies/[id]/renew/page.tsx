'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { getRenewalPreview, renewMyPolicy } from '@/lib/api/policyApi';
import type { IRenewalPreviewResponse } from '@/lib/types/policy';

export default function RenewalPreviewPage() {
  const params = useParams();
  const router = useRouter();
  const policyId = Number(params.id);

  const [preview, setPreview] = useState<IRenewalPreviewResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [renewing, setRenewing] = useState(false);
  const [success, setSuccess] = useState<{ id: number; policyNumber: string } | null>(null);

  useEffect(() => {
    setLoading(true);
    getRenewalPreview(policyId)
      .then(setPreview)
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, [policyId]);

  async function handleConfirmRenewal() {
    setRenewing(true);
    setError('');
    try {
      const result = await renewMyPolicy(policyId);
      setSuccess({ id: result.id, policyNumber: result.policyNumber });
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Renewal failed';
      setError(message);
    } finally {
      setRenewing(false);
    }
  }

  if (loading) {
    return (
      <div className="flex justify-center py-20">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-200 border-t-primary-600" />
      </div>
    );
  }

  if (error && !preview) {
    return (
      <div className="card mx-auto max-w-2xl text-center text-red-600">
        <p>Error: {error}</p>
        <Link
          href={`/policies/${policyId}`}
          className="mt-2 inline-block text-primary-600 hover:underline"
        >
          Back to Policy
        </Link>
      </div>
    );
  }

  if (success) {
    return (
      <div className="mx-auto max-w-2xl">
        <div className="card text-center">
          <div className="mb-4 text-4xl text-green-500">&#10003;</div>
          <h1 className="mb-2 text-2xl font-bold text-gray-900">
            Policy Renewed Successfully
          </h1>
          <p className="mb-1 text-gray-600">
            Your new policy number is{' '}
            <span className="font-semibold">{success.policyNumber}</span>
          </p>
          <p className="mb-6 text-sm text-gray-500">
            Coverage is active immediately.
          </p>
          <div className="flex justify-center gap-4">
            <Link
              href={`/policies/${success.id}`}
              className="btn-primary"
            >
              View New Policy
            </Link>
            <Link
              href="/policies"
              className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              Back to Policies
            </Link>
          </div>
        </div>
      </div>
    );
  }

  if (!preview) return null;

  const premiumIncreased = preview.premiumDifference > 0;
  const premiumDecreased = preview.premiumDifference < 0;

  return (
    <div className="mx-auto max-w-2xl">
      <Link
        href={`/policies/${policyId}`}
        className="mb-4 inline-block text-sm text-primary-600 hover:underline"
      >
        &larr; Back to Policy
      </Link>

      <div className="card">
        <h1 className="mb-1 text-2xl font-bold text-gray-900">
          Renew Policy {preview.policyNumber}
        </h1>
        <p className="mb-6 text-sm text-gray-500">
          Review your recalculated premium before confirming renewal.
        </p>

        {/* Premium Comparison */}
        <div className="mb-6 grid gap-4 sm:grid-cols-3">
          <div className="rounded-lg border border-gray-200 p-4 text-center">
            <p className="text-xs text-gray-500">Current Premium</p>
            <p className="text-xl font-bold text-gray-600">
              ${preview.currentPremium.toFixed(2)}
            </p>
          </div>
          <div className="rounded-lg border border-gray-200 p-4 text-center">
            <p className="text-xs text-gray-500">New Premium</p>
            <p className="text-xl font-bold text-primary-700">
              ${preview.renewalPremium.toFixed(2)}
            </p>
          </div>
          <div className="rounded-lg border border-gray-200 p-4 text-center">
            <p className="text-xs text-gray-500">Difference</p>
            <p
              className={`text-xl font-bold ${
                premiumIncreased
                  ? 'text-red-600'
                  : premiumDecreased
                    ? 'text-green-600'
                    : 'text-gray-600'
              }`}
            >
              {premiumIncreased ? '+' : ''}
              ${preview.premiumDifference.toFixed(2)}
            </p>
          </div>
        </div>

        {/* Premium Breakdown */}
        <div className="mb-6">
          <h2 className="mb-3 text-sm font-semibold text-gray-700">
            Premium Breakdown
          </h2>
          <div className="overflow-hidden rounded-lg border border-gray-200">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-2 text-left text-xs font-medium uppercase text-gray-500">
                    Factor
                  </th>
                  <th className="px-4 py-2 text-left text-xs font-medium uppercase text-gray-500">
                    Value
                  </th>
                  <th className="px-4 py-2 text-right text-xs font-medium uppercase text-gray-500">
                    Impact
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {preview.premiumBreakdown.map((item, idx) => (
                  <tr key={idx}>
                    <td className="px-4 py-2 text-sm capitalize text-gray-900">
                      {item.factor.replace(/_/g, ' ')}
                    </td>
                    <td className="px-4 py-2 text-sm text-gray-600">
                      {item.value}
                    </td>
                    <td
                      className={`px-4 py-2 text-right text-sm font-medium ${
                        item.impact > 0
                          ? 'text-red-600'
                          : item.impact < 0
                            ? 'text-green-600'
                            : 'text-gray-500'
                      }`}
                    >
                      {item.impact > 0 ? '+' : ''}
                      ${item.impact.toFixed(2)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* New Coverage Dates */}
        <div className="mb-6 grid gap-4 sm:grid-cols-2">
          <div>
            <p className="text-xs text-gray-500">New Effective Date</p>
            <p className="text-sm font-medium text-gray-900">
              {new Date(preview.effectiveDate).toLocaleDateString()}
            </p>
          </div>
          <div>
            <p className="text-xs text-gray-500">New Expiration Date</p>
            <p className="text-sm font-medium text-gray-900">
              {new Date(preview.expirationDate).toLocaleDateString()}
            </p>
          </div>
        </div>

        {error && (
          <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
            {error}
          </div>
        )}

        {/* Actions */}
        <div className="flex gap-3">
          <button
            onClick={handleConfirmRenewal}
            disabled={renewing}
            className="btn-primary flex-1"
          >
            {renewing ? 'Processing Renewal...' : 'Confirm Renewal'}
          </button>
          <Link
            href={`/policies/${policyId}`}
            className="flex items-center justify-center rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            Cancel
          </Link>
        </div>
      </div>
    </div>
  );
}
