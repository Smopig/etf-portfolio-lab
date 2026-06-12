import type { Metadata } from "next";
import "./globals.css";

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
      <body className="min-h-screen bg-background text-foreground antialiased">
        {children}
      </body>
    </html>
  );
}
