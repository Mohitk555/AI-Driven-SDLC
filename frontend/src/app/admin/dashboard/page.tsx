'use client';

import { useState, useEffect, useCallback } from 'react';
import DashboardLayout from '../../../components/dashboard/DashboardLayout';
import KpiCardGrid from '../../../components/dashboard/KpiCardGrid';
import SalesActivityChart from '../../../components/dashboard/SalesActivityChart';
import SalesAnalyticsChart from '../../../components/dashboard/SalesAnalyticsChart';
import RecentOrdersTable from '../../../components/dashboard/RecentOrdersTable';
import { IDashboardData } from '../../../lib/types/dashboard';
import { fetchDashboardData } from '../../../lib/mock/dashboardData';

export default function AdminDashboardPage() {
  const [data, setData] = useState<IDashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(() => {
    setLoading(true);
    setError(null);
    fetchDashboardData()
      .then(setData)
      .catch(() => setError('Failed to load dashboard data'))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  return (
    <DashboardLayout>
      <div className="flex flex-col gap-6">
        {/* KPI Cards Row */}
        <KpiCardGrid
          cards={data?.kpiCards ?? []}
          loading={loading}
          error={error}
          onRetry={loadData}
        />

        {/* Charts Row */}
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1fr_0.7fr]">
          <SalesActivityChart initialData={data?.salesActivity ?? []} />
          <SalesAnalyticsChart initialData={data?.salesAnalytics ?? []} />
        </div>

        {/* Recent Orders */}
        <RecentOrdersTable
          orders={data?.recentOrders ?? []}
          loading={loading}
          error={error}
          onRetry={loadData}
        />
      </div>
    </DashboardLayout>
  );
}
