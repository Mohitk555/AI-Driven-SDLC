'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { getPolicy, downloadPolicyDocument } from '@/lib/api/policyApi';
import type { IPolicyResponse } from '@/lib/types/policy';
import StatusBadge from '@/components/shared/StatusBadge';

export default function PolicyDetailPage() {
  const params = useParams();
  const policyId = Number(params.id);

  const [policy, setPolicy] = useState<IPolicyResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [downloading, setDownloading] = useState(false);

  useEffect(() => {
    setLoading(true);
    getPolicy(policyId)
      .then(setPolicy)
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, [policyId]);

  async function handleDownload() {
    if (!policy) return;
    setDownloading(true);
    try {
      const blob = await downloadPolicyDocument(policy.id);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `policy-${policy.policyNumber}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : 'Download failed';
      setError(message);
    } finally {
      setDownloading(false);
    }
  }

  if (loading) {
    return (
      <div className="flex justify-center py-20">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-200 border-t-primary-600" />
      </div>
    );
  }

  if (error && !policy) {
    return (
      <div className="card text-center text-red-600">
        <p>Error: {error}</p>
        <Link
          href="/policies"
          className="mt-2 inline-block text-primary-600 hover:underline"
        >
          Back to Policies
        </Link>
      </div>
    );
  }

  if (!policy) return null;

  const isRenewable =
    policy.status === 'active' ||
    policy.status === 'expired' ||
    policy.status === 'reinstated';
  const alreadyRenewed = policy.renewedToPolicyId !== null;
  const isCancelled = policy.status === 'cancelled';

  const daysUntilExpiry = Math.ceil(
    (new Date(policy.expirationDate).getTime() - Date.now()) / (1000 * 60 * 60 * 24)
  );
  const isExpiringSoon = isRenewable && daysUntilExpiry <= 30 && daysUntilExpiry >= 0;

  return (
    <div className="mx-auto max-w-3xl">
      <Link
        href="/policies"
        className="mb-4 inline-block text-sm text-primary-600 hover:underline"
      >
        &larr; Back to Policies
      </Link>

      {/* Expiry Warning */}
      {isExpiringSoon && !alreadyRenewed && (
        <div className="mb-4 rounded-lg border border-amber-300 bg-amber-50 p-4">
          <p className="text-sm font-semibold text-amber-800">
            &#9888; This policy {daysUntilExpiry === 0 ? 'expires today' : `expires in ${daysUntilExpiry} days`} ({new Date(policy.expirationDate).toLocaleDateString()})
          </p>
          <p className="mt-1 text-xs text-amber-700">
            Renew now to maintain your coverage without interruption.
          </p>
        </div>
      )}

      <div className="card">
        <div className="mb-6 flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">
              Policy {policy.policyNumber}
            </h1>
            <p className="mt-1 text-sm capitalize text-gray-500">
              {policy.coverageType} Coverage
            </p>
          </div>
          <StatusBadge status={policy.status} />
        </div>

        <div className="mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <div>
            <p className="text-sm text-gray-500">Premium Amount</p>
            <p className="text-2xl font-bold text-primary-700">
              ${policy.premiumAmount.toFixed(2)}
            </p>
          </div>
          <div>
            <p className="text-sm text-gray-500">Effective Date</p>
            <p className="text-sm font-medium text-gray-900">
              {new Date(policy.effectiveDate).toLocaleDateString()}
            </p>
          </div>
          <div>
            <p className="text-sm text-gray-500">Expiration Date</p>
            <p className="text-sm font-medium text-gray-900">
              {new Date(policy.expirationDate).toLocaleDateString()}
            </p>
          </div>
          <div>
            <p className="text-sm text-gray-500">Quote ID</p>
            <p className="text-sm font-medium text-gray-900">
              {policy.quoteId}
            </p>
          </div>
          <div>
            <p className="text-sm text-gray-500">Created</p>
            <p className="text-sm font-medium text-gray-900">
              {new Date(policy.createdAt).toLocaleDateString()}
            </p>
          </div>
        </div>

        {/* Renewal Chain Links */}
        {(policy.renewedFromPolicyId || policy.renewedToPolicyId) && (
          <div className="mb-6 rounded-lg border border-blue-200 bg-blue-50 p-4">
            <h3 className="mb-2 text-sm font-semibold text-blue-800">
              Renewal History
            </h3>
            <div className="space-y-1">
              {policy.renewedFromPolicyId && (
                <p className="text-sm text-blue-700">
                  Renewed from:{' '}
                  <Link
                    href={`/policies/${policy.renewedFromPolicyId}`}
                    className="font-medium underline hover:text-blue-900"
                  >
                    Policy #{policy.renewedFromPolicyId}
                  </Link>
                </p>
              )}
              {policy.renewedToPolicyId && (
                <p className="text-sm text-blue-700">
                  Renewed as:{' '}
                  <Link
                    href={`/policies/${policy.renewedToPolicyId}`}
                    className="font-medium underline hover:text-blue-900"
                  >
                    Policy #{policy.renewedToPolicyId}
                  </Link>
                </p>
              )}
            </div>
          </div>
        )}

        {error && (
          <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
            {error}
          </div>
        )}

        <div className="space-y-3">
          {/* Renewal Button */}
          {isRenewable && !alreadyRenewed && (
            <Link
              href={`/policies/${policy.id}/renew`}
              className="btn-primary block w-full text-center"
            >
              Renew This Policy
            </Link>
          )}

          {alreadyRenewed && (
            <div className="rounded-lg border border-green-200 bg-green-50 p-3 text-center text-sm text-green-700">
              This policy has been renewed.{' '}
              <Link
                href={`/policies/${policy.renewedToPolicyId}`}
                className="font-medium underline"
              >
                View renewed policy
              </Link>
            </div>
          )}

          {isCancelled && !alreadyRenewed && (
            <div className="rounded-lg border border-gray-200 bg-gray-50 p-3 text-center text-sm text-gray-600">
              This policy is cancelled. Contact support to reinstate before renewal.
            </div>
          )}

          <button
            onClick={handleDownload}
            disabled={downloading}
            className="w-full rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            {downloading ? 'Downloading...' : 'Download Policy Document'}
          </button>
        </div>
      </div>
    </div>
  );
}
