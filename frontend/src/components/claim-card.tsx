"use client";

import Link from "next/link";
import type { Claim } from "@/lib/api";
import ClaimStatusBadge from "./claim-status-badge";

interface ClaimCardProps {
  claim: Claim;
}

const CLAIM_TYPE_ICONS: Record<string, string> = {
  auto: "\u{1F697}",
  health: "\u{1FA7A}",
  property: "\u{1F3E0}",
  life: "\u{1F6E1}\uFE0F",
};

export default function ClaimCard({ claim }: ClaimCardProps) {
  const icon = CLAIM_TYPE_ICONS[claim.claim_type] || "\u{1F4CB}";
  const date = new Date(claim.created_at).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });

  return (
    <Link href={`/claims/${claim.id}`}>
      <div className="card cursor-pointer transition-shadow hover:shadow-md">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <span className="text-2xl" role="img" aria-label={claim.claim_type}>
              {icon}
            </span>
            <div>
              <p className="text-sm font-semibold text-gray-900 capitalize">
                {claim.claim_type} Claim
              </p>
              <p className="text-xs text-gray-500">
                Policy: {claim.policy_number}
              </p>
            </div>
          </div>
          <ClaimStatusBadge status={claim.status} />
        </div>
        <div className="mt-4 flex items-end justify-between">
          <p className="text-lg font-bold text-gray-900">
            ${claim.amount.toLocaleString("en-US", { minimumFractionDigits: 2 })}
          </p>
          <p className="text-xs text-gray-400">{date}</p>
        </div>
      </div>
    </Link>
  );
}
