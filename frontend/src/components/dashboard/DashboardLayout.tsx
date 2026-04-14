'use client';

import DashboardSidebar from './DashboardSidebar';
import DashboardHeader from './DashboardHeader';

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen bg-[#F5F6FA]">
      <DashboardSidebar />
      <div className="ml-[98px] flex-1">
        <DashboardHeader />
        <main className="px-8 pb-8">{children}</main>
      </div>
    </div>
  );
}
