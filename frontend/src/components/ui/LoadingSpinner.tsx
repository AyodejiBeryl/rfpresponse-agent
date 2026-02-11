export function LoadingSpinner({ className = "" }: { className?: string }) {
  return (
    <div className={`flex items-center justify-center ${className}`}>
      <div className="h-8 w-8 animate-spin rounded-full border-4 border-gray-200 border-t-primary-600" />
    </div>
  );
}

export function PageLoading() {
  return (
    <div className="flex h-[50vh] items-center justify-center">
      <div className="text-center">
        <div className="h-10 w-10 animate-spin rounded-full border-4 border-gray-200 border-t-primary-600 mx-auto" />
        <p className="mt-4 text-sm text-gray-400">Loading...</p>
      </div>
    </div>
  );
}
