'use client';

import { Search, Bell, Globe, ChevronDown } from 'lucide-react';

export default function DashboardHeader() {
  return (
    <header className="flex h-[100px] items-center justify-between px-8">
      <div className="flex flex-col">
        <h1 className="text-[28px] font-bold text-[#061B2B]" style={{ fontFamily: 'DM Sans, sans-serif' }}>
          Good Morning, Jacob
        </h1>
        <p className="text-[20px] text-[#667085]" style={{ fontFamily: 'DM Sans, sans-serif' }}>
          Welcome to UIDASH!
        </p>
      </div>

      <div className="flex items-center gap-4">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={18} />
          <input
            type="text"
            placeholder="Search..."
            className="h-12 w-[300px] rounded-xl border border-gray-200 bg-white pl-10 pr-4 text-sm text-gray-700 placeholder:text-gray-400 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
          />
        </div>

        <div className="flex h-12 items-center gap-2 rounded-xl border border-gray-200 bg-white px-4 text-sm text-gray-600">
          <span>English</span>
          <ChevronDown size={16} />
        </div>

        <button className="relative flex h-[60px] w-[60px] items-center justify-center rounded-xl border border-gray-200 bg-white transition-colors hover:bg-gray-50">
          <Bell size={22} className="text-gray-600" />
          <span className="absolute right-3 top-3 h-2.5 w-2.5 rounded-full bg-red-500 ring-2 ring-white" />
        </button>

        <button className="relative flex h-[60px] w-[60px] items-center justify-center rounded-xl border border-gray-200 bg-white transition-colors hover:bg-gray-50">
          <Globe size={22} className="text-gray-600" />
        </button>

        <div className="flex h-[60px] w-[60px] items-center justify-center rounded-xl bg-indigo-100">
          <div className="h-10 w-10 rounded-full bg-indigo-600 flex items-center justify-center text-white font-semibold text-sm">
            JD
          </div>
        </div>
      </div>
    </header>
  );
}
