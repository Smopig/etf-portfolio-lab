import type { Metadata } from "next";
import "./globals.css";
import AppShell from "@/components/layout/AppShell";

export const metadata: Metadata = {
  title: "ETF Portfolio Lab",
  description: "ETF 研究分析工具",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-Hant" className="dark">
      <body className="min-h-screen bg-bg-base text-text-primary antialiased">
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
