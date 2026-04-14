import Link from 'next/link';

export default function HomePage() {
  return (
    <div className="flex flex-col items-center justify-center py-20 text-center">
      <h1 className="text-4xl font-bold text-gray-900">
        Auto Insurance Management
      </h1>
      <p className="mt-4 max-w-lg text-lg text-gray-600">
        Get a quote for your vehicle, compare coverage options, and purchase
        your auto insurance policy — all in one place.
      </p>
      <div className="mt-8 flex gap-4">
        <Link href="/quotes/new" className="btn-primary">
          Get a Quote
        </Link>
        <Link href="/policies" className="btn-secondary">
          View Policies
        </Link>
      </div>
    </div>
  );
}
