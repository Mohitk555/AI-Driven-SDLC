"use client";

interface IAuthFormProps {
  className?: string;
}

/**
 * Create / edit form for auth
 */
export default function AuthForm({ className }: IAuthFormProps) {
  return (
    <section className={className}>
      <h2 className="text-xl font-semibold mb-4">AuthForm</h2>
      {/* TODO: implement AuthForm */}
      <p className="text-gray-500">Create / edit form for auth</p>
    </section>
  );
}
