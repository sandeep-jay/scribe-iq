import type { Metadata } from "next";

import { AppShell } from "@/components/AppShell";
import "./globals.css";

const themeBootstrap = `(function(){try{var k='scribe-iq-theme';var v=localStorage.getItem(k);var d=v==='dark'||(!v&&window.matchMedia('(prefers-color-scheme: dark)').matches);document.documentElement.classList.toggle('dark',d);}catch(e){}})();`;

export const metadata: Metadata = {
  title: "Scribe-IQ — Healthcare AI Platform Prototype",
  description: "Grounded clinical documentation workflows over a synthetic corpus, with auditable AI.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="antialiased" suppressHydrationWarning>
        <script dangerouslySetInnerHTML={{ __html: themeBootstrap }} />
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
