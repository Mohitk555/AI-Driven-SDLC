"use client";

interface IQuotingFormProps {
  className?: string;
}

/**
 * Create / edit form for quoting
 */
export default function QuotingForm({ className }: IQuotingFormProps) {
  return (
    <section className={className}>
      <h2 className="text-xl font-semibold mb-4">QuotingForm</h2>
      {/* TODO: implement QuotingForm */}
      <p className="text-gray-500">Create / edit form for quoting</p>
    </section>
  );
}
