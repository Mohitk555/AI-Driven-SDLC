"use client";

interface IUserFormProps {
  className?: string;
}

/**
 * Create / edit form for user
 */
export default function UserForm({ className }: IUserFormProps) {
  return (
    <section className={className}>
      <h2 className="text-xl font-semibold mb-4">UserForm</h2>
      {/* TODO: implement UserForm */}
      <p className="text-gray-500">Create / edit form for user</p>
    </section>
  );
}
