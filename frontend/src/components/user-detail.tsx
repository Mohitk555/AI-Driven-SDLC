"use client";

interface IUserDetailProps {
  className?: string;
}

/**
 * Detail view for a single user
 */
export default function UserDetail({ className }: IUserDetailProps) {
  return (
    <section className={className}>
      <h2 className="text-xl font-semibold mb-4">UserDetail</h2>
      {/* TODO: implement UserDetail */}
      <p className="text-gray-500">Detail view for a single user</p>
    </section>
  );
}
