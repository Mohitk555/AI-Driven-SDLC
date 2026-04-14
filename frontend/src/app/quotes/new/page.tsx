'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { createQuote } from '@/lib/api/policyApi';
import type { IQuoteCreateRequest } from '@/lib/types/policy';

const initialForm: IQuoteCreateRequest = {
  vehicle: { make: '', model: '', year: new Date().getFullYear(), vin: '', mileage: 0 },
  driver: {
    firstName: '',
    lastName: '',
    dateOfBirth: '',
    licenseNumber: '',
    address: { street: '', city: '', state: '', zipCode: '' },
    drivingHistory: { accidentCount: 0, violationCount: 0, yearsLicensed: 0 },
  },
  coverageType: 'basic',
};

export default function NewQuotePage() {
  const router = useRouter();
  const [form, setForm] = useState<IQuoteCreateRequest>(initialForm);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  function setVehicle<K extends keyof IQuoteCreateRequest['vehicle']>(
    key: K,
    value: IQuoteCreateRequest['vehicle'][K]
  ) {
    setForm((prev) => ({ ...prev, vehicle: { ...prev.vehicle, [key]: value } }));
  }

  function setDriver<K extends keyof IQuoteCreateRequest['driver']>(
    key: K,
    value: IQuoteCreateRequest['driver'][K]
  ) {
    setForm((prev) => ({ ...prev, driver: { ...prev.driver, [key]: value } }));
  }

  function setAddress<K extends keyof IQuoteCreateRequest['driver']['address']>(
    key: K,
    value: string
  ) {
    setForm((prev) => ({
      ...prev,
      driver: { ...prev.driver, address: { ...prev.driver.address, [key]: value } },
    }));
  }

  function setHistory<K extends keyof IQuoteCreateRequest['driver']['drivingHistory']>(
    key: K,
    value: number
  ) {
    setForm((prev) => ({
      ...prev,
      driver: {
        ...prev.driver,
        drivingHistory: { ...prev.driver.drivingHistory, [key]: value },
      },
    }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      const quote = await createQuote(form);
      router.push(`/quotes/${quote.id}`);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to create quote';
      setError(message);
    } finally {
      setLoading(false);
    }
  }

  const inputClass = 'input-field';
  const labelClass = 'block text-sm font-medium text-gray-700 mb-1';

  return (
    <div className="mx-auto max-w-3xl">
      <h1 className="mb-6 text-2xl font-bold text-gray-900">Get a Quote</h1>

      {error && (
        <div className="mb-6 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-8">
        {/* Vehicle Details */}
        <section className="card">
          <h2 className="mb-4 text-lg font-semibold text-gray-800">Vehicle Details</h2>
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className={labelClass}>Make</label>
              <input
                className={inputClass}
                required
                value={form.vehicle.make}
                onChange={(e) => setVehicle('make', e.target.value)}
                placeholder="e.g. Toyota"
              />
            </div>
            <div>
              <label className={labelClass}>Model</label>
              <input
                className={inputClass}
                required
                value={form.vehicle.model}
                onChange={(e) => setVehicle('model', e.target.value)}
                placeholder="e.g. Camry"
              />
            </div>
            <div>
              <label className={labelClass}>Year</label>
              <input
                className={inputClass}
                type="number"
                required
                min={1900}
                max={new Date().getFullYear() + 1}
                value={form.vehicle.year}
                onChange={(e) => setVehicle('year', parseInt(e.target.value) || 0)}
              />
            </div>
            <div>
              <label className={labelClass}>VIN</label>
              <input
                className={inputClass}
                required
                value={form.vehicle.vin}
                onChange={(e) => setVehicle('vin', e.target.value)}
                placeholder="17-character VIN"
              />
            </div>
            <div>
              <label className={labelClass}>Mileage</label>
              <input
                className={inputClass}
                type="number"
                required
                min={0}
                value={form.vehicle.mileage}
                onChange={(e) => setVehicle('mileage', parseInt(e.target.value) || 0)}
              />
            </div>
          </div>
        </section>

        {/* Driver Details */}
        <section className="card">
          <h2 className="mb-4 text-lg font-semibold text-gray-800">Driver Details</h2>
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className={labelClass}>First Name</label>
              <input
                className={inputClass}
                required
                value={form.driver.firstName}
                onChange={(e) => setDriver('firstName', e.target.value)}
              />
            </div>
            <div>
              <label className={labelClass}>Last Name</label>
              <input
                className={inputClass}
                required
                value={form.driver.lastName}
                onChange={(e) => setDriver('lastName', e.target.value)}
              />
            </div>
            <div>
              <label className={labelClass}>Date of Birth</label>
              <input
                className={inputClass}
                type="date"
                required
                value={form.driver.dateOfBirth}
                onChange={(e) => setDriver('dateOfBirth', e.target.value)}
              />
            </div>
            <div>
              <label className={labelClass}>License Number</label>
              <input
                className={inputClass}
                required
                value={form.driver.licenseNumber}
                onChange={(e) => setDriver('licenseNumber', e.target.value)}
              />
            </div>
          </div>

          <h3 className="mb-3 mt-6 text-sm font-semibold text-gray-700">Address</h3>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="sm:col-span-2">
              <label className={labelClass}>Street</label>
              <input
                className={inputClass}
                required
                value={form.driver.address.street}
                onChange={(e) => setAddress('street', e.target.value)}
              />
            </div>
            <div>
              <label className={labelClass}>City</label>
              <input
                className={inputClass}
                required
                value={form.driver.address.city}
                onChange={(e) => setAddress('city', e.target.value)}
              />
            </div>
            <div>
              <label className={labelClass}>State</label>
              <input
                className={inputClass}
                required
                value={form.driver.address.state}
                onChange={(e) => setAddress('state', e.target.value)}
                placeholder="e.g. CA"
              />
            </div>
            <div>
              <label className={labelClass}>Zip Code</label>
              <input
                className={inputClass}
                required
                value={form.driver.address.zipCode}
                onChange={(e) => setAddress('zipCode', e.target.value)}
              />
            </div>
          </div>

          <h3 className="mb-3 mt-6 text-sm font-semibold text-gray-700">
            Driving History
          </h3>
          <div className="grid gap-4 sm:grid-cols-3">
            <div>
              <label className={labelClass}>Accidents</label>
              <input
                className={inputClass}
                type="number"
                min={0}
                required
                value={form.driver.drivingHistory.accidentCount}
                onChange={(e) =>
                  setHistory('accidentCount', parseInt(e.target.value) || 0)
                }
              />
            </div>
            <div>
              <label className={labelClass}>Violations</label>
              <input
                className={inputClass}
                type="number"
                min={0}
                required
                value={form.driver.drivingHistory.violationCount}
                onChange={(e) =>
                  setHistory('violationCount', parseInt(e.target.value) || 0)
                }
              />
            </div>
            <div>
              <label className={labelClass}>Years Licensed</label>
              <input
                className={inputClass}
                type="number"
                min={0}
                required
                value={form.driver.drivingHistory.yearsLicensed}
                onChange={(e) =>
                  setHistory('yearsLicensed', parseInt(e.target.value) || 0)
                }
              />
            </div>
          </div>
        </section>

        {/* Coverage Selection */}
        <section className="card">
          <h2 className="mb-4 text-lg font-semibold text-gray-800">Coverage Type</h2>
          <div className="flex gap-6">
            <label className="flex cursor-pointer items-center gap-2">
              <input
                type="radio"
                name="coverage"
                value="basic"
                checked={form.coverageType === 'basic'}
                onChange={() => setForm((prev) => ({ ...prev, coverageType: 'basic' }))}
                className="h-4 w-4 text-primary-600 focus:ring-primary-500"
              />
              <span className="text-sm font-medium text-gray-700">
                Basic Coverage
              </span>
            </label>
            <label className="flex cursor-pointer items-center gap-2">
              <input
                type="radio"
                name="coverage"
                value="full"
                checked={form.coverageType === 'full'}
                onChange={() => setForm((prev) => ({ ...prev, coverageType: 'full' }))}
                className="h-4 w-4 text-primary-600 focus:ring-primary-500"
              />
              <span className="text-sm font-medium text-gray-700">
                Full Coverage
              </span>
            </label>
          </div>
        </section>

        <button type="submit" disabled={loading} className="btn-primary w-full">
          {loading ? 'Generating Quote...' : 'Get Quote'}
        </button>
      </form>
    </div>
  );
}
