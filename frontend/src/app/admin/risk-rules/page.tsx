'use client';

import { useEffect, useState, useCallback } from 'react';
import Link from 'next/link';
import { getRiskRules, toggleRiskRule, deleteRiskRule } from '@/lib/api/policyApi';
import type { IRiskRuleResponse } from '@/lib/types/policy';

export default function AdminRiskRulesPage() {
  const [rules, setRules] = useState<IRiskRuleResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [toast, setToast] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  const fetchRules = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const result = await getRiskRules();
      setRules(result.items);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load risk rules');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchRules();
  }, [fetchRules]);

  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => setToast(null), 3000);
    return () => clearTimeout(t);
  }, [toast]);

  const handleToggle = async (rule: IRiskRuleResponse) => {
    try {
      const updated = await toggleRiskRule(rule.id);
      setRules((prev) => prev.map((r) => (r.id === updated.id ? updated : r)));
      setToast({
        type: 'success',
        message: `Rule "${rule.label}" ${updated.isEnabled ? 'enabled' : 'disabled'}.`,
      });
    } catch (err: unknown) {
      setToast({ type: 'error', message: err instanceof Error ? err.message : 'Toggle failed' });
    }
  };

  const handleDelete = async (rule: IRiskRuleResponse) => {
    if (!confirm(`Are you sure you want to delete the rule "${rule.label}"?`)) return;
    try {
      await deleteRiskRule(rule.id);
      setRules((prev) => prev.filter((r) => r.id !== rule.id));
      setToast({ type: 'success', message: `Rule "${rule.label}" deleted.` });
    } catch (err: unknown) {
      setToast({ type: 'error', message: err instanceof Error ? err.message : 'Delete failed' });
    }
  };

  return (
    <div>
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Admin &mdash; Risk Rules</h1>
        <Link
          href="/admin/risk-rules/new"
          className="rounded-md bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700"
        >
          Create New Rule
        </Link>
      </div>

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

      {/* Loading / Error / Table */}
      {loading ? (
        <div className="mt-12 flex justify-center">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-gray-300 border-t-primary-600" />
        </div>
      ) : error ? (
        <p className="mt-8 text-center text-red-600">{error}</p>
      ) : (
        <div className="mt-6 overflow-x-auto rounded-lg border border-gray-200">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                {['Factor Name', 'Label', 'Status', 'Brackets', 'Actions'].map((h) => (
                  <th
                    key={h}
                    className="whitespace-nowrap px-4 py-3 text-left font-semibold text-gray-700"
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {rules.map((rule) => (
                <tr key={rule.id} className="hover:bg-gray-50">
                  <td className="whitespace-nowrap px-4 py-3 font-medium">{rule.factorName}</td>
                  <td className="px-4 py-3">{rule.label}</td>
                  <td className="px-4 py-3">
                    <button
                      onClick={() => handleToggle(rule)}
                      className={`rounded-full px-3 py-1 text-xs font-medium ${
                        rule.isEnabled
                          ? 'bg-green-100 text-green-800 hover:bg-green-200'
                          : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                      }`}
                    >
                      {rule.isEnabled ? 'Enabled' : 'Disabled'}
                    </button>
                  </td>
                  <td className="px-4 py-3">{rule.brackets.length}</td>
                  <td className="whitespace-nowrap px-4 py-3">
                    <div className="flex gap-1">
                      <Link
                        href={`/admin/risk-rules/${rule.id}/edit`}
                        className="rounded bg-blue-50 px-2 py-1 text-xs font-medium text-blue-700 hover:bg-blue-100"
                      >
                        Edit
                      </Link>
                      <button
                        onClick={() => handleDelete(rule)}
                        className="rounded bg-red-50 px-2 py-1 text-xs font-medium text-red-700 hover:bg-red-100"
                      >
                        Delete
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {rules.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-4 py-8 text-center text-gray-500">
                    No risk rules found. Create one to get started.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
