"use client";

interface ILayoutProps {
  className?: string;
}

/**
 * Root layout with navigation and footer
 */
export default function Layout({ className }: ILayoutProps) {
  return (
    <section className={className}>
      <h2 className="text-xl font-semibold mb-4">Layout</h2>
      {/* TODO: implement Layout */}
      <p className="text-gray-500">Root layout with navigation and footer</p>
    </section>
  );
}
