"use client";

interface IQuotingDetailProps {
  className?: string;
}

/**
 * Detail view for a single quoting
 */
export default function QuotingDetail({ className }: IQuotingDetailProps) {
  return (
    <section className={className}>
      <h2 className="text-xl font-semibold mb-4">QuotingDetail</h2>
      {/* TODO: implement QuotingDetail */}
      <p className="text-gray-500">Detail view for a single quoting</p>
    </section>
  );
}
