'use client';

import { useEffect, useState, useCallback } from 'react';
import StatusBadge from '@/components/shared/StatusBadge';
import Pagination from '@/components/shared/Pagination';
import {
  getAdminPolicies,
  cancelPolicy,
  renewPolicy,
  reinstatePolicy,
} from '@/lib/api/policyApi';
import type { IAdminPolicyItem, IAdminPolicyListResponse } from '@/lib/types/policy';

const STATUS_OPTIONS = ['All', 'Active', 'Expired', 'Cancelled', 'Reinstated'];

function ActionModal({
  title,
  onConfirm,
  onCancel,
  needsReason,
}: {
  title: string;
  onConfirm: (reason: string) => void;
  onCancel: () => void;
  needsReason: boolean;
}) {
  const [reason, setReason] = useState('');
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="w-full max-w-md rounded-lg bg-white p-6 shadow-xl">
        <h3 className="text-lg font-semibold text-gray-900">{title}</h3>
        {needsReason && (
          <textarea
            className="mt-3 w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
            rows={3}
            placeholder="Enter reason..."
            value={reason}
            onChange={(e) => setReason(e.target.value)}
          />
        )}
        <div className="mt-4 flex justify-end gap-2">
          <button onClick={onCancel} className="btn-secondary text-sm">
            Cancel
          </button>
          <button
            onClick={() => onConfirm(reason)}
            disabled={needsReason && !reason.trim()}
            className="rounded-md bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-40"
          >
            Confirm
          </button>
        </div>
      </div>
    </div>
  );
}

export default function AdminPoliciesPage() {
  const [data, setData] = useState<IAdminPolicyListResponse | null>(null);
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState('');
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [toast, setToast] = useState<{ type: 'success' | 'error'; message: string } | null>(null);
  const [modal, setModal] = useState<{
    action: 'cancel' | 'renew' | 'reinstate';
    policy: IAdminPolicyItem;
  } | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const result = await getAdminPolicies(page, status || undefined, search || undefined);
      setData(result);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load policies');
    } finally {
      setLoading(false);
    }
  }, [page, status, search]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => setToast(null), 3000);
    return () => clearTimeout(t);
  }, [toast]);

  const handleAction = async (reason: string) => {
    if (!modal) return;
    try {
      if (modal.action === 'cancel') await cancelPolicy(modal.policy.id, reason);
      else if (modal.action === 'renew') await renewPolicy(modal.policy.id);
      else await reinstatePolicy(modal.policy.id, reason);
      setToast({ type: 'success', message: `Policy ${modal.policy.policyNumber} ${modal.action}ed successfully.` });
      setModal(null);
      fetchData();
    } catch (err: unknown) {
      setToast({ type: 'error', message: err instanceof Error ? err.message : 'Action failed' });
      setModal(null);
    }
  };

  const canCancel = (s: string) => ['active', 'reinstated'].includes(s.toLowerCase());
  const canRenew = (s: string) => ['active', 'expired'].includes(s.toLowerCase());
  const canReinstate = (s: string) => s.toLowerCase() === 'cancelled';

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900">Admin &mdash; Policies</h1>

      {/* Toast */}
      {toast && (
        <div
          className={`mt-4 rounded-md px-4 py-3 text-sm font-medium ${
            toast.type === 'success' ? 'bg-green-50 text-green-800' : 'bg-red-50 text-red-800'
          }`}
        >
          {toast.message}
        </div>
      )}

      {/* Filters */}
      <div className="mt-6 flex flex-wrap items-center gap-4">
        <select
          value={status}
          onChange={(e) => { setStatus(e.target.value); setPage(1); }}
          className="rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
        >
          {STATUS_OPTIONS.map((s) => (
            <option key={s} value={s === 'All' ? '' : s.toLowerCase()}>
              {s}
            </option>
          ))}
        </select>
        <input
          type="text"
          placeholder="Search by policy # or customer..."
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1); }}
          className="w-72 rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
        />
      </div>

      {/* Loading / Error / Table */}
      {loading ? (
        <div className="mt-12 flex justify-center">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-gray-300 border-t-primary-600" />
        </div>
      ) : error ? (
        <p className="mt-8 text-center text-red-600">{error}</p>
      ) : (
        <>
          <div className="mt-6 overflow-x-auto rounded-lg border border-gray-200">
            <table className="min-w-full divide-y divide-gray-200 text-sm">
              <thead className="bg-gray-50">
                <tr>
                  {['Policy #', 'Customer', 'Vehicle', 'Coverage', 'Premium ($)', 'Status', 'Effective', 'Expiration', 'Actions'].map((h) => (
                    <th key={h} className="whitespace-nowrap px-4 py-3 text-left font-semibold text-gray-700">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {data?.items.map((p) => (
                  <tr key={p.id} className="hover:bg-gray-50">
                    <td className="whitespace-nowrap px-4 py-3 font-medium">{p.policyNumber}</td>
                    <td className="px-4 py-3">{p.customerName}</td>
                    <td className="px-4 py-3">{p.vehicleSummary}</td>
                    <td className="px-4 py-3 capitalize">{p.coverageType}</td>
                    <td className="px-4 py-3">{p.premiumAmount.toFixed(2)}</td>
                    <td className="px-4 py-3"><StatusBadge status={p.status} /></td>
                    <td className="whitespace-nowrap px-4 py-3">{p.effectiveDate}</td>
                    <td className="whitespace-nowrap px-4 py-3">{p.expirationDate}</td>
                    <td className="whitespace-nowrap px-4 py-3">
                      <div className="flex gap-1">
                        {canCancel(p.status) && (
                          <button onClick={() => setModal({ action: 'cancel', policy: p })} className="rounded bg-red-50 px-2 py-1 text-xs font-medium text-red-700 hover:bg-red-100">Cancel</button>
                        )}
                        {canRenew(p.status) && (
                          <button onClick={() => setModal({ action: 'renew', policy: p })} className="rounded bg-blue-50 px-2 py-1 text-xs font-medium text-blue-700 hover:bg-blue-100">Renew</button>
                        )}
                        {canReinstate(p.status) && (
                          <button onClick={() => setModal({ action: 'reinstate', policy: p })} className="rounded bg-green-50 px-2 py-1 text-xs font-medium text-green-700 hover:bg-green-100">Reinstate</button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
                {data?.items.length === 0 && (
                  <tr>
                    <td colSpan={9} className="px-4 py-8 text-center text-gray-500">No policies found.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
          {data && (
            <Pagination page={data.page} total={data.total} pageSize={data.pageSize} onPageChange={setPage} />
          )}
        </>
      )}

      {/* Modal */}
      {modal && (
        <ActionModal
          title={`${modal.action.charAt(0).toUpperCase() + modal.action.slice(1)} Policy ${modal.policy.policyNumber}?`}
          needsReason={modal.action !== 'renew'}
          onConfirm={handleAction}
          onCancel={() => setModal(null)}
        />
      )}
    </div>
  );
}
