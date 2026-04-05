"use client";

interface IPolicyFormProps {
  className?: string;
}

/**
 * Create / edit form for policy
 */
export default function PolicyForm({ className }: IPolicyFormProps) {
  return (
    <section className={className}>
      <h2 className="text-xl font-semibold mb-4">PolicyForm</h2>
      {/* TODO: implement PolicyForm */}
      <p className="text-gray-500">Create / edit form for policy</p>
    </section>
  );
}
