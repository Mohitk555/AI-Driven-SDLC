"use client";

interface INotificationFormProps {
  className?: string;
}

/**
 * Create / edit form for notification
 */
export default function NotificationForm({ className }: INotificationFormProps) {
  return (
    <section className={className}>
      <h2 className="text-xl font-semibold mb-4">NotificationForm</h2>
      {/* TODO: implement NotificationForm */}
      <p className="text-gray-500">Create / edit form for notification</p>
    </section>
  );
}
