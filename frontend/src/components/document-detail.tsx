"use client";

interface IDocumentDetailProps {
  className?: string;
}

/**
 * Detail view for a single document
 */
export default function DocumentDetail({ className }: IDocumentDetailProps) {
  return (
    <section className={className}>
      <h2 className="text-xl font-semibold mb-4">DocumentDetail</h2>
      {/* TODO: implement DocumentDetail */}
      <p className="text-gray-500">Detail view for a single document</p>
    </section>
  );
}
