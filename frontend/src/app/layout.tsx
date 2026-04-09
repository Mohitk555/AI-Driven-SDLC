import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'InsureOS — Auto Insurance Platform',
  description: 'Manage your auto insurance quotes and policies',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <nav className="border-b border-gray-200 bg-white">
          <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3 sm:px-6 lg:px-8">
            <a href="/" className="text-xl font-bold text-primary-700">
              InsureOS
            </a>
            <div className="flex items-center gap-6 text-sm font-medium text-gray-600">
              <a href="/quotes" className="hover:text-primary-600">
                Quotes
              </a>
              <a href="/policies" className="hover:text-primary-600">
                Policies
              </a>
              <a href="/admin/policies" className="hover:text-primary-600">
                Admin Policies
              </a>
            </div>
          </div>
        </nav>
        <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
          {children}
        </main>
      </body>
    </html>
  );
}
