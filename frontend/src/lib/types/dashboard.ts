export interface IKpiCard {
  id: string;
  label: string;
  value: string;
  change: number;
  changeLabel: string;
  sparklineData: number[];
  icon: 'dollar' | 'cart' | 'users' | 'trending';
}

export interface ISalesDataPoint {
  date: string;
  amount: number;
}

export interface ISalesAnalyticsItem {
  label: string;
  value: number;
}

export interface IRecentOrder {
  id: string;
  item: string;
  quantity: number;
  orderDate: string;
  amount: number;
  status: 'PAID' | 'PENDING' | 'CANCELLED' | 'REFUNDED';
}

export interface IDashboardData {
  kpiCards: IKpiCard[];
  salesActivity: ISalesDataPoint[];
  salesAnalytics: ISalesAnalyticsItem[];
  recentOrders: IRecentOrder[];
}

export type DateRange = 'weekly' | 'monthly' | 'yearly';
