"use client";

interface IPolicyDetailProps {
  className?: string;
}

/**
 * Detail view for a single policy
 */
export default function PolicyDetail({ className }: IPolicyDetailProps) {
  return (
    <section className={className}>
      <h2 className="text-xl font-semibold mb-4">PolicyDetail</h2>
      {/* TODO: implement PolicyDetail */}
      <p className="text-gray-500">Detail view for a single policy</p>
    </section>
  );
}
