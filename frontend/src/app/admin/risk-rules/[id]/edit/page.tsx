'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { getRiskRules, updateRiskRule } from '@/lib/api/policyApi';
import type { IBracketItem, IRiskRuleResponse } from '@/lib/types/policy';

export default function EditRiskRulePage() {
  const params = useParams();
  const router = useRouter();
  const ruleId = Number(params.id);

  const [rule, setRule] = useState<IRiskRuleResponse | null>(null);
  const [label, setLabel] = useState('');
  const [brackets, setBrackets] = useState<IBracketItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    async function load() {
      try {
        const result = await getRiskRules();
        const found = result.items.find((r) => r.id === ruleId);
        if (!found) {
          setError('Risk rule not found.');
          return;
        }
        setRule(found);
        setLabel(found.label);
        setBrackets(found.brackets.map((b) => ({ ...b })));
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : 'Failed to load rule');
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [ruleId]);

  const addBracket = () => {
    setBrackets((prev) => [...prev, { condition: '', adjustment: 0 }]);
  };

  const removeBracket = (index: number) => {
    setBrackets((prev) => prev.filter((_, i) => i !== index));
  };

  const updateBracketField = (index: number, field: keyof IBracketItem, value: string | number) => {
    setBrackets((prev) =>
      prev.map((b, i) => (i === index ? { ...b, [field]: value } : b))
    );
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (brackets.length === 0) {
      setError('At least one bracket is required.');
      return;
    }
    setSubmitting(true);
    setError('');
    try {
      await updateRiskRule(ruleId, { label, brackets });
      router.push('/admin/risk-rules');
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to update rule');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="mt-12 flex justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-gray-300 border-t-primary-600" />
      </div>
    );
  }

  if (!rule && error) {
    return <p className="mt-8 text-center text-red-600">{error}</p>;
  }

  return (
    <div className="mx-auto max-w-2xl">
      <h1 className="text-2xl font-bold text-gray-900">
        Edit Risk Rule &mdash; {rule?.factorName}
      </h1>

      {error && (
        <div className="mt-4 rounded-md bg-red-50 px-4 py-3 text-sm font-medium text-red-800">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="mt-6 space-y-6">
        <div>
          <label className="block text-sm font-medium text-gray-700">Factor Name</label>
          <input
            type="text"
            disabled
            value={rule?.factorName ?? ''}
            className="mt-1 w-full rounded-md border border-gray-200 bg-gray-100 px-3 py-2 text-sm text-gray-500"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700">Label</label>
          <input
            type="text"
            required
            value={label}
            onChange={(e) => setLabel(e.target.value)}
            className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
          />
        </div>

        {/* Brackets Editor */}
        <div>
          <div className="flex items-center justify-between">
            <label className="block text-sm font-medium text-gray-700">Brackets</label>
            <button
              type="button"
              onClick={addBracket}
              className="rounded-md bg-primary-600 px-3 py-1 text-xs font-medium text-white hover:bg-primary-700"
            >
              Add Bracket
            </button>
          </div>
          <div className="mt-2 space-y-3">
            {brackets.map((bracket, index) => (
              <div key={index} className="flex items-center gap-3 rounded-md border border-gray-200 bg-gray-50 p-3">
                <div className="flex-1">
                  <label className="block text-xs text-gray-500">Condition</label>
                  <input
                    type="text"
                    required
                    value={bracket.condition}
                    onChange={(e) => updateBracketField(index, 'condition', e.target.value)}
                    placeholder="e.g. age < 25"
                    className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
                  />
                </div>
                <div className="w-32">
                  <label className="block text-xs text-gray-500">Adjustment (%)</label>
                  <input
                    type="number"
                    required
                    value={bracket.adjustment}
                    onChange={(e) => updateBracketField(index, 'adjustment', parseFloat(e.target.value) || 0)}
                    className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
                  />
                </div>
                <button
                  type="button"
                  onClick={() => removeBracket(index)}
                  disabled={brackets.length <= 1}
                  className="mt-5 rounded bg-red-50 px-2 py-1 text-xs font-medium text-red-700 hover:bg-red-100 disabled:opacity-40"
                >
                  Remove
                </button>
              </div>
            ))}
          </div>
        </div>

        <div className="flex gap-3">
          <button
            type="submit"
            disabled={submitting}
            className="rounded-md bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-40"
          >
            {submitting ? 'Saving...' : 'Save Changes'}
          </button>
          <Link
            href="/admin/risk-rules"
            className="rounded-md border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            Cancel
          </Link>
        </div>
      </form>
    </div>
  );
}
