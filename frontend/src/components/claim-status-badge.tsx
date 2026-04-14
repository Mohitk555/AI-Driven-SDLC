"use client";

import type { ClaimStatus } from "@/lib/api";

interface ClaimStatusBadgeProps {
  status: ClaimStatus;
}

const STATUS_CONFIG: Record<
  ClaimStatus,
  { label: string; className: string }
> = {
  submitted: {
    label: "Submitted",
    className: "bg-blue-100 text-blue-800 ring-blue-600/20",
  },
  under_review: {
    label: "Under Review",
    className: "bg-yellow-100 text-yellow-800 ring-yellow-600/20",
  },
  approved: {
    label: "Approved",
    className: "bg-green-100 text-green-800 ring-green-600/20",
  },
  rejected: {
    label: "Rejected",
    className: "bg-red-100 text-red-800 ring-red-600/20",
  },
  info_required: {
    label: "Info Required",
    className: "bg-orange-100 text-orange-800 ring-orange-600/20",
  },
};

export default function ClaimStatusBadge({ status }: ClaimStatusBadgeProps) {
  const config = STATUS_CONFIG[status] || {
    label: status,
    className: "bg-gray-100 text-gray-800 ring-gray-600/20",
  };

  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ring-1 ring-inset ${config.className}`}
    >
      {config.label}
    </span>
  );
}
