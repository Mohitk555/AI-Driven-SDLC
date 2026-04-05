"use client";

interface IDashboardProps {
  className?: string;
}

/**
 * Main dashboard with summary cards
 */
export default function Dashboard({ className }: IDashboardProps) {
  return (
    <section className={className}>
      <h2 className="text-xl font-semibold mb-4">Dashboard</h2>
      {/* TODO: implement Dashboard */}
      <p className="text-gray-500">Main dashboard with summary cards</p>
    </section>
  );
}
