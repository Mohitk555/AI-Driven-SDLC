"use client";

interface IPolicyListProps {
  className?: string;
}

/**
 * Table listing all policys
 */
export default function PolicyList({ className }: IPolicyListProps) {
  return (
    <section className={className}>
      <h2 className="text-xl font-semibold mb-4">PolicyList</h2>
      {/* TODO: implement PolicyList */}
      <p className="text-gray-500">Table listing all policys</p>
    </section>
  );
}
