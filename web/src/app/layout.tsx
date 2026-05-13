import type { Metadata } from "next";
import "../styles/globals.css";
import "../components/tour/tour.css";
import { Providers } from "./providers";
import { Sidebar } from "@/components/layout/Sidebar";
import { Footer } from "@/components/layout/Footer";
import { TourMount } from "@/components/tour/TourMount";

export const metadata: Metadata = {
  title: "FlightCast — Database-Native ML Audit",
  description:
    "Aviation demand forecasting with MariaDB system-versioned temporal tables and MAPIE conformal prediction. MariaDB Hackathon Malaysia 2026.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen text-slate-200">
        <Providers>
          <div className="flex min-h-screen">
            <Sidebar />
            <div className="flex-1 flex flex-col min-w-0">
              <main className="flex-1 w-full max-w-[1280px] px-7 py-6 mx-auto">
                {children}
              </main>
              <Footer />
            </div>
          </div>
          <TourMount />
        </Providers>
      </body>
    </html>
  );
}
