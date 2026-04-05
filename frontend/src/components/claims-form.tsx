"use client";

interface IClaimsFormProps {
  className?: string;
}

/**
 * Create / edit form for claims
 */
export default function ClaimsForm({ className }: IClaimsFormProps) {
  return (
    <section className={className}>
      <h2 className="text-xl font-semibold mb-4">ClaimsForm</h2>
      {/* TODO: implement ClaimsForm */}
      <p className="text-gray-500">Create / edit form for claims</p>
    </section>
  );
}
