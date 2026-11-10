import React from "react";
import { AlertCircle } from "lucide-react";

export default function ErrorState({ message = "Something went wrong.", onRetry }) {
  return <div className="flex min-h-52 flex-col items-center justify-center rounded-2xl border border-dashed border-rose-200 bg-rose-50 px-6 py-10 text-center">
    <AlertCircle className="h-7 w-7 text-rose-500" />
    <p className="mt-3 font-medium text-rose-700">{message}</p>
    {onRetry && <button onClick={onRetry} className="mt-4 rounded-lg bg-rose-600 px-4 py-2 text-sm font-semibold text-white hover:bg-rose-700">Try again</button>}
  </div>;
}