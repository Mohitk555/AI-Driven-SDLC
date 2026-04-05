"use client";

interface IDocumentFormProps {
  className?: string;
}

/**
 * Create / edit form for document
 */
export default function DocumentForm({ className }: IDocumentFormProps) {
  return (
    <section className={className}>
      <h2 className="text-xl font-semibold mb-4">DocumentForm</h2>
      {/* TODO: implement DocumentForm */}
      <p className="text-gray-500">Create / edit form for document</p>
    </section>
  );
}
