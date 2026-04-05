"use client";

interface IClaimsListProps {
  className?: string;
}

/**
 * Table listing all claimss
 */
export default function ClaimsList({ className }: IClaimsListProps) {
  return (
    <section className={className}>
      <h2 className="text-xl font-semibold mb-4">ClaimsList</h2>
      {/* TODO: implement ClaimsList */}
      <p className="text-gray-500">Table listing all claimss</p>
    </section>
  );
}
