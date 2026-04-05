"use client";

interface INotificationDetailProps {
  className?: string;
}

/**
 * Detail view for a single notification
 */
export default function NotificationDetail({ className }: INotificationDetailProps) {
  return (
    <section className={className}>
      <h2 className="text-xl font-semibold mb-4">NotificationDetail</h2>
      {/* TODO: implement NotificationDetail */}
      <p className="text-gray-500">Detail view for a single notification</p>
    </section>
  );
}
