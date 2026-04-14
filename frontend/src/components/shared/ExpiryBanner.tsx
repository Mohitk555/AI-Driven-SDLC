'use client';

import Link from 'next/link';
import type { IExpiringPolicyItem } from '@/lib/types/policy';

interface ExpiryBannerProps {
  policies: IExpiringPolicyItem[];
}

export default function ExpiryBanner({ policies }: ExpiryBannerProps) {
  if (policies.length === 0) return null;

  return (
    <div className="mb-6 space-y-3">
      {policies.map((policy) => {
        const isUrgent = policy.daysUntilExpiry <= 7;
        const bgClass = isUrgent
          ? 'border-red-300 bg-red-50'
          : 'border-amber-300 bg-amber-50';
        const textClass = isUrgent ? 'text-red-800' : 'text-amber-800';
        const iconColor = isUrgent ? 'text-red-500' : 'text-amber-500';

        const expiryText =
          policy.daysUntilExpiry === 0
            ? 'Expires today'
            : policy.daysUntilExpiry === 1
              ? 'Expires tomorrow'
              : `Expires in ${policy.daysUntilExpiry} days`;

        return (
          <div
            key={policy.id}
            className={`flex items-center justify-between rounded-lg border p-4 ${bgClass}`}
          >
            <div className="flex items-center gap-3">
              <span className={`text-xl ${iconColor}`}>&#9888;</span>
              <div>
                <p className={`text-sm font-semibold ${textClass}`}>
                  {expiryText} &mdash; Policy {policy.policyNumber}
                </p>
                <p className={`text-xs ${textClass} opacity-75`}>
                  {policy.coverageType} coverage &middot; ${policy.premiumAmount.toFixed(2)}/yr
                  &middot; Expires{' '}
                  {new Date(policy.expirationDate).toLocaleDateString()}
                </p>
              </div>
            </div>
            <Link
              href={`/policies/${policy.id}/renew`}
              className={`rounded-lg px-4 py-2 text-sm font-medium text-white ${
                isUrgent
                  ? 'bg-red-600 hover:bg-red-700'
                  : 'bg-amber-600 hover:bg-amber-700'
              }`}
            >
              Renew Now
            </Link>
          </div>
        );
      })}
    </div>
  );
}
