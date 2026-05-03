import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Sidebar } from "@/components/Sidebar";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Agentic Book Generator",
  description: "Human-in-the-loop book generation system",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${inter.className} text-slate-900`}>
        <div className="min-h-screen bg-slate-50 flex relative overflow-hidden">
          {/* Background Blobs */}
          <div className="absolute -top-24 -right-24 h-[500px] w-[500px] rounded-full bg-blue-200/40 blur-3xl pointer-events-none z-0" />
          <div className="absolute bottom-0 left-1/3 h-[500px] w-[500px] rounded-full bg-indigo-200/30 blur-3xl pointer-events-none z-0" />
          
          <Sidebar />
          <main className="flex-1 p-8 h-screen overflow-y-auto relative z-10">
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}
