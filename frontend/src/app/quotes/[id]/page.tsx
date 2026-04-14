'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { getQuote, purchasePolicy } from '@/lib/api/policyApi';
import type { IQuoteResponse, IPolicyResponse } from '@/lib/types/policy';
import StatusBadge from '@/components/shared/StatusBadge';

export default function QuoteDetailPage() {
  const params = useParams();
  const router = useRouter();
  const quoteId = Number(params.id);

  const [quote, setQuote] = useState<IQuoteResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [purchasing, setPurchasing] = useState(false);
  const [policy, setPolicy] = useState<IPolicyResponse | null>(null);

  useEffect(() => {
    setLoading(true);
    getQuote(quoteId)
      .then(setQuote)
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, [quoteId]);

  async function handlePurchase() {
    setPurchasing(true);
    setError('');
    try {
      const result = await purchasePolicy(quoteId);
      setPolicy(result);
      setQuote((prev) => (prev ? { ...prev, status: 'purchased' } : prev));
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Purchase failed';
      setError(message);
    } finally {
      setPurchasing(false);
    }
  }

  if (loading) {
    return (
      <div className="flex justify-center py-20">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-200 border-t-primary-600" />
      </div>
    );
  }

  if (error && !quote) {
    return (
      <div className="card text-center text-red-600">
        <p>Error: {error}</p>
        <Link href="/quotes" className="mt-2 inline-block text-primary-600 hover:underline">
          Back to Quotes
        </Link>
      </div>
    );
  }

  if (!quote) return null;

  return (
    <div className="mx-auto max-w-3xl">
      <Link href="/quotes" className="mb-4 inline-block text-sm text-primary-600 hover:underline">
        &larr; Back to Quotes
      </Link>

      <div className="card">
        <div className="mb-6 flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">
              {quote.vehicleYear} {quote.vehicleMake} {quote.vehicleModel}
            </h1>
            <p className="mt-1 text-sm capitalize text-gray-500">
              {quote.coverageType} Coverage
            </p>
          </div>
          <StatusBadge status={quote.status} />
        </div>

        <div className="mb-6 grid gap-4 sm:grid-cols-3">
          <div>
            <p className="text-sm text-gray-500">Premium Amount</p>
            <p className="text-2xl font-bold text-primary-700">
              ${quote.premiumAmount.toFixed(2)}
            </p>
          </div>
          <div>
            <p className="text-sm text-gray-500">Created</p>
            <p className="text-sm font-medium text-gray-900">
              {new Date(quote.createdAt).toLocaleDateString()}
            </p>
          </div>
          <div>
            <p className="text-sm text-gray-500">Expires</p>
            <p className="text-sm font-medium text-gray-900">
              {new Date(quote.expiresAt).toLocaleDateString()}
            </p>
          </div>
        </div>

        {/* Premium Breakdown */}
        {quote.premiumBreakdown && quote.premiumBreakdown.length > 0 && (
          <div className="mb-6">
            <h2 className="mb-3 text-lg font-semibold text-gray-800">
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
                  {quote.premiumBreakdown.map((item, idx) => (
                    <tr key={idx}>
                      <td className="px-4 py-2 text-sm text-gray-900">
                        {item.factor}
                      </td>
                      <td className="px-4 py-2 text-sm text-gray-600">
                        {item.value}
                      </td>
                      <td className="px-4 py-2 text-right text-sm font-medium">
                        <span
                          className={
                            item.impact >= 0 ? 'text-red-600' : 'text-green-600'
                          }
                        >
                          {item.impact >= 0 ? '+' : ''}${item.impact.toFixed(2)}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {error && (
          <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
            {error}
          </div>
        )}

        {/* Actions based on status */}
        {quote.status === 'pending' && (
          <button
            onClick={handlePurchase}
            disabled={purchasing}
            className="btn-primary w-full"
          >
            {purchasing ? 'Processing...' : 'Purchase Policy'}
          </button>
        )}

        {quote.status === 'expired' && (
          <div className="rounded-lg border border-yellow-200 bg-yellow-50 p-4 text-center text-sm text-yellow-800">
            This quote has expired. Please{' '}
            <Link href="/quotes/new" className="font-medium underline">
              create a new quote
            </Link>
            .
          </div>
        )}

        {quote.status === 'purchased' && policy && (
          <Link
            href={`/policies/${policy.id}`}
            className="btn-primary inline-block w-full text-center"
          >
            View Policy
          </Link>
        )}

        {quote.status === 'purchased' && !policy && (
          <div className="rounded-lg border border-green-200 bg-green-50 p-4 text-center text-sm text-green-800">
            This quote has been purchased.{' '}
            <Link href="/policies" className="font-medium underline">
              View your policies
            </Link>
            .
          </div>
        )}
      </div>
    </div>
  );
}
