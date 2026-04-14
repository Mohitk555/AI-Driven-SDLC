'use client';

import {
  LayoutDashboard,
  ShoppingCart,
  Package,
  BarChart3,
  MessageSquare,
  Settings,
  HelpCircle,
  LogOut,
  User,
  Sun,
  Moon,
} from 'lucide-react';
import { useState } from 'react';

const navItems = [
  { icon: LayoutDashboard, label: 'Dashboard', href: '/admin/dashboard', active: true },
  { icon: ShoppingCart, label: 'Orders', href: '#' },
  { icon: Package, label: 'Products', href: '#' },
  { icon: BarChart3, label: 'Analytics', href: '#' },
  { icon: MessageSquare, label: 'Messages', href: '#' },
  { icon: Settings, label: 'Settings', href: '#' },
  { icon: HelpCircle, label: 'Help', href: '#' },
];

export default function DashboardSidebar() {
  const [darkMode, setDarkMode] = useState(true);

  return (
    <aside className="fixed left-0 top-0 z-40 flex h-screen w-[98px] flex-col items-center bg-[#1E1E2D] py-6">
      <div className="mb-8 flex h-10 w-10 items-center justify-center rounded-lg bg-indigo-600 text-white font-bold text-lg">
        U
      </div>

      <nav className="flex flex-1 flex-col items-center gap-2">
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <a
              key={item.label}
              href={item.href}
              className={`flex h-12 w-12 items-center justify-center rounded-xl transition-colors ${
                item.active
                  ? 'bg-indigo-600 text-white'
                  : 'text-gray-400 hover:bg-[#2A2A3C] hover:text-white'
              }`}
              title={item.label}
            >
              <Icon size={22} />
            </a>
          );
        })}
      </nav>

      <div className="mt-auto flex flex-col items-center gap-3 pb-4">
        <button
          onClick={() => setDarkMode(!darkMode)}
          className="flex h-10 w-10 items-center justify-center rounded-lg text-gray-400 hover:text-white transition-colors"
          title={darkMode ? 'Light Mode' : 'Dark Mode'}
        >
          {darkMode ? <Sun size={20} /> : <Moon size={20} />}
        </button>
        <a
          href="#"
          className="flex h-10 w-10 items-center justify-center rounded-lg text-gray-400 hover:text-white transition-colors"
          title="Profile"
        >
          <User size={20} />
        </a>
        <a
          href="#"
          className="flex h-10 w-10 items-center justify-center rounded-lg text-gray-400 hover:text-red-400 transition-colors"
          title="Logout"
        >
          <LogOut size={20} />
        </a>
      </div>
    </aside>
  );
}
