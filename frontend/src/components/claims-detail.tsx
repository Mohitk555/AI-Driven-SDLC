"use client";

interface IClaimsDetailProps {
  className?: string;
}

/**
 * Detail view for a single claims
 */
export default function ClaimsDetail({ className }: IClaimsDetailProps) {
  return (
    <section className={className}>
      <h2 className="text-xl font-semibold mb-4">ClaimsDetail</h2>
      {/* TODO: implement ClaimsDetail */}
      <p className="text-gray-500">Detail view for a single claims</p>
    </section>
  );
}
