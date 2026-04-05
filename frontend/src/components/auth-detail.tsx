"use client";

interface IAuthDetailProps {
  className?: string;
}

/**
 * Detail view for a single auth
 */
export default function AuthDetail({ className }: IAuthDetailProps) {
  return (
    <section className={className}>
      <h2 className="text-xl font-semibold mb-4">AuthDetail</h2>
      {/* TODO: implement AuthDetail */}
      <p className="text-gray-500">Detail view for a single auth</p>
    </section>
  );
}
