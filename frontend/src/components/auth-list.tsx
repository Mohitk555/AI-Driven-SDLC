"use client";

interface IAuthListProps {
  className?: string;
}

/**
 * Table listing all auths
 */
export default function AuthList({ className }: IAuthListProps) {
  return (
    <section className={className}>
      <h2 className="text-xl font-semibold mb-4">AuthList</h2>
      {/* TODO: implement AuthList */}
      <p className="text-gray-500">Table listing all auths</p>
    </section>
  );
}
