"use client";

interface INotificationListProps {
  className?: string;
}

/**
 * Table listing all notifications
 */
export default function NotificationList({ className }: INotificationListProps) {
  return (
    <section className={className}>
      <h2 className="text-xl font-semibold mb-4">NotificationList</h2>
      {/* TODO: implement NotificationList */}
      <p className="text-gray-500">Table listing all notifications</p>
    </section>
  );
}
