"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";
import { TourProvider } from "@/components/tour/TourProvider";

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            // Static-ish data (batches / routes / coverage) doesn't
            // change during a session. Treating cache as fresh for
            // 5 min eliminates redundant refetches on page nav.
            staleTime: 5 * 60_000,
            // Keep data in memory for 30 min after last use, so
            // navigating back to a page is instant.
            gcTime: 30 * 60_000,
            refetchOnWindowFocus: false,
            refetchOnReconnect: false,
            // Single retry on failure (was Tanstack default = 3)
            retry: 1,
          },
        },
      }),
  );
  return (
    <QueryClientProvider client={queryClient}>
      <TourProvider>{children}</TourProvider>
    </QueryClientProvider>
  );
}
