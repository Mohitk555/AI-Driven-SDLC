"use client";

interface IDocumentListProps {
  className?: string;
}

/**
 * Table listing all documents
 */
export default function DocumentList({ className }: IDocumentListProps) {
  return (
    <section className={className}>
      <h2 className="text-xl font-semibold mb-4">DocumentList</h2>
      {/* TODO: implement DocumentList */}
      <p className="text-gray-500">Table listing all documents</p>
    </section>
  );
}
