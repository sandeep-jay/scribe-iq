import type { Metadata } from "next";
import Link from "next/link";
import { Geist, Geist_Mono } from "next/font/google";

import { ThemeToggle } from "@/components/ThemeToggle";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

const themeBootstrap = `(function(){try{var k='scribe-iq-theme';var v=localStorage.getItem(k);var d=v==='dark'||(!v&&window.matchMedia('(prefers-color-scheme: dark)').matches);document.documentElement.classList.toggle('dark',d);}catch(e){}})();`;

export const metadata: Metadata = {
  title: "Scribe-IQ Demo",
  description: "Chat-first grounded RAG demo",
};

function NavShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-40 border-b border-zinc-200 bg-white/80 backdrop-blur dark:border-zinc-800 dark:bg-zinc-950/80">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-6 py-3">
          <Link href="/patients" className="font-semibold tracking-tight">
            Scribe-IQ
          </Link>
          <div className="flex items-center gap-4">
            <nav className="flex gap-6 text-sm text-zinc-600 dark:text-zinc-300">
              <Link className="hover:text-zinc-900 dark:hover:text-white" href="/patients">
                Patients
              </Link>
              <Link className="hover:text-zinc-900 dark:hover:text-white" href="/chat">
                Chat
              </Link>
            </nav>
            <ThemeToggle />
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-6 py-10">{children}</main>
    </div>
  );
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${geistSans.variable} ${geistMono.variable} antialiased`}>
        <script dangerouslySetInnerHTML={{ __html: themeBootstrap }} />
        <NavShell>{children}</NavShell>
      </body>
    </html>
  );
}
