"use client";

interface ILoginFormProps {
  className?: string;
}

/**
 * Authentication login form
 */
export default function LoginForm({ className }: ILoginFormProps) {
  return (
    <section className={className}>
      <h2 className="text-xl font-semibold mb-4">LoginForm</h2>
      {/* TODO: implement LoginForm */}
      <p className="text-gray-500">Authentication login form</p>
    </section>
  );
}
