import { IDashboardData, ISalesDataPoint, ISalesAnalyticsItem } from '../types/dashboard';

export const dashboardData: IDashboardData = {
  kpiCards: [
    {
      id: 'todays-sales',
      label: "Today's Sales",
      value: '$5,345',
      change: 12.5,
      changeLabel: 'vs yesterday',
      sparklineData: [30, 40, 35, 50, 49, 60, 70, 91, 80, 85, 90, 95],
      icon: 'dollar',
    },
    {
      id: 'total-sales',
      label: 'Total Sales',
      value: '$124,563',
      change: 8.2,
      changeLabel: 'vs last month',
      sparklineData: [20, 30, 45, 55, 40, 60, 50, 70, 65, 80, 75, 90],
      icon: 'trending',
    },
    {
      id: 'total-orders',
      label: 'Total Orders',
      value: '1,456',
      change: -2.4,
      changeLabel: 'vs last month',
      sparklineData: [60, 55, 50, 65, 70, 55, 45, 50, 60, 55, 48, 52],
      icon: 'cart',
    },
    {
      id: 'total-customers',
      label: 'Total Customers',
      value: '3,567',
      change: 5.8,
      changeLabel: 'vs last month',
      sparklineData: [40, 45, 50, 55, 60, 58, 65, 70, 75, 72, 78, 82],
      icon: 'users',
    },
  ],

  salesActivity: generateSalesActivity(),

  salesAnalytics: [
    { label: 'Jan', value: 4500 },
    { label: 'Feb', value: 3800 },
    { label: 'Mar', value: 5200 },
    { label: 'Apr', value: 4900 },
    { label: 'May', value: 6100 },
    { label: 'Jun', value: 5400 },
    { label: 'Jul', value: 7200 },
    { label: 'Aug', value: 6800 },
    { label: 'Sep', value: 5900 },
  ],

  recentOrders: [
    {
      id: '#215613',
      item: 'Premium Auto Policy',
      quantity: 1,
      orderDate: '11/10/2020',
      amount: 99.0,
      status: 'PENDING',
    },
    {
      id: '#214314',
      item: 'Basic Coverage Plan',
      quantity: 1,
      orderDate: '11/10/2020',
      amount: 249.0,
      status: 'PAID',
    },
    {
      id: '#316899',
      item: 'Full Coverage Bundle',
      quantity: 1,
      orderDate: '11/10/2020',
      amount: 49.0,
      status: 'PAID',
    },
    {
      id: '#184920',
      item: 'Roadside Assistance',
      quantity: 2,
      orderDate: '11/09/2020',
      amount: 150.0,
      status: 'CANCELLED',
    },
    {
      id: '#293847',
      item: 'Liability Only Plan',
      quantity: 1,
      orderDate: '11/08/2020',
      amount: 320.0,
      status: 'PAID',
    },
    {
      id: '#102938',
      item: 'Collision Add-On',
      quantity: 1,
      orderDate: '11/07/2020',
      amount: 85.0,
      status: 'PENDING',
    },
  ],
};

function generateSalesActivity(): ISalesDataPoint[] {
  const data: ISalesDataPoint[] = [];
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const values = [4200, 3800, 5100, 4700, 6300, 5800, 7100, 6500, 5900, 6800, 7500, 8200];
  for (let i = 0; i < months.length; i++) {
    data.push({ date: months[i], amount: values[i] });
  }
  return data;
}

export function fetchDashboardData(): Promise<IDashboardData> {
  return new Promise((resolve) => {
    setTimeout(() => resolve(dashboardData), 800);
  });
}

export function fetchSalesActivityByRange(range: string): Promise<ISalesDataPoint[]> {
  const rangeData: Record<string, ISalesDataPoint[]> = {
    weekly: [
      { date: 'Mon', amount: 1200 },
      { date: 'Tue', amount: 1500 },
      { date: 'Wed', amount: 1100 },
      { date: 'Thu', amount: 1800 },
      { date: 'Fri', amount: 2100 },
      { date: 'Sat', amount: 1700 },
      { date: 'Sun', amount: 900 },
    ],
    monthly: dashboardData.salesActivity,
    yearly: [
      { date: '2019', amount: 42000 },
      { date: '2020', amount: 58000 },
      { date: '2021', amount: 65000 },
      { date: '2022', amount: 78000 },
      { date: '2023', amount: 92000 },
      { date: '2024', amount: 110000 },
    ],
  };
  return new Promise((resolve) => {
    setTimeout(() => resolve(rangeData[range] || dashboardData.salesActivity), 500);
  });
}

export function fetchSalesAnalyticsByRange(range: string): Promise<ISalesAnalyticsItem[]> {
  const rangeData: Record<string, ISalesAnalyticsItem[]> = {
    weekly: [
      { label: 'Mon', value: 1200 },
      { label: 'Tue', value: 1500 },
      { label: 'Wed', value: 1100 },
      { label: 'Thu', value: 1800 },
      { label: 'Fri', value: 2100 },
      { label: 'Sat', value: 1700 },
      { label: 'Sun', value: 900 },
    ],
    monthly: dashboardData.salesAnalytics,
    yearly: [
      { label: '2019', value: 42000 },
      { label: '2020', value: 58000 },
      { label: '2021', value: 65000 },
      { label: '2022', value: 78000 },
      { label: '2023', value: 92000 },
      { label: '2024', value: 110000 },
    ],
  };
  return new Promise((resolve) => {
    setTimeout(() => resolve(rangeData[range] || dashboardData.salesAnalytics), 500);
  });
}
