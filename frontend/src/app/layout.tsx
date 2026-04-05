import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "InsureOS",
  description: "AI-powered Insurance Operating System",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <nav className="border-b px-6 py-3 flex items-center justify-between">
          <span className="font-bold text-lg">InsureOS</span>
          <div className="flex gap-4">
            <a href="/dashboard">Dashboard</a>
            <a href="/policies">Policies</a>
            <a href="/claims">Claims</a>
          </div>
        </nav>
        <main className="p-6">{children}</main>
      </body>
    </html>
  );
}
