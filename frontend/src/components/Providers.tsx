"use client";

import { SWRConfig } from "swr";
import { fetcher } from "@/lib/api";
import { ToastProvider } from "@/components/ui/toast";

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <SWRConfig
      value={{
        fetcher,
        // 4xx responses won't fix themselves; don't hammer the API.
        onErrorRetry: (err, _key, _config, revalidate, { retryCount }) => {
          if (err?.status && err.status < 500) return;
          if (retryCount >= 3) return;
          setTimeout(() => revalidate({ retryCount }), 3000 * (retryCount + 1));
        },
      }}
    >
      <ToastProvider>{children}</ToastProvider>
    </SWRConfig>
  );
}
