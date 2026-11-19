import type { Metadata } from "next";
import { Geist_Mono, Plus_Jakarta_Sans } from "next/font/google";
import "./globals.css";
import Nav from "@/components/Nav";

const jakarta = Plus_Jakarta_Sans({ variable: "--font-plus-jakarta-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Executive Assistant",
  description: "Executive Assistant Agent - calendar, mail triage and approvals",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${jakarta.variable} ${geistMono.variable} h-full antialiased`}>
      <body className="min-h-full md:flex">
        <aside className="border-b border-border bg-surface px-4 py-4 md:sticky md:top-0 md:flex md:h-screen md:w-60 md:shrink-0 md:flex-col md:border-b-0 md:border-r md:px-5 md:py-6">
          <div className="flex items-center gap-3 md:mb-8">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-accent text-sm font-semibold text-accent-foreground">
              EA
            </div>
            <div>
              <p className="text-sm font-semibold leading-tight">Executive Assistant</p>
              <p className="text-xs text-muted">Assistant console</p>
            </div>
          </div>
          <div className="mt-4 md:mt-0">
            <Nav />
          </div>
        </aside>
        <main className="flex-1 px-4 py-8 md:px-10 md:py-10">
          <div className="mx-auto max-w-5xl">{children}</div>
        </main>
      </body>
    </html>
  );
}
