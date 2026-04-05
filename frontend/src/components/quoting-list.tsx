"use client";

interface IQuotingListProps {
  className?: string;
}

/**
 * Table listing all quotings
 */
export default function QuotingList({ className }: IQuotingListProps) {
  return (
    <section className={className}>
      <h2 className="text-xl font-semibold mb-4">QuotingList</h2>
      {/* TODO: implement QuotingList */}
      <p className="text-gray-500">Table listing all quotings</p>
    </section>
  );
}
