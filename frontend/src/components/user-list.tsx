"use client";

interface IUserListProps {
  className?: string;
}

/**
 * Table listing all users
 */
export default function UserList({ className }: IUserListProps) {
  return (
    <section className={className}>
      <h2 className="text-xl font-semibold mb-4">UserList</h2>
      {/* TODO: implement UserList */}
      <p className="text-gray-500">Table listing all users</p>
    </section>
  );
}
