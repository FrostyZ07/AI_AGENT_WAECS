import type { Metadata } from "next";
import "./globals.css";
import Nav from "@/components/Nav";

export const metadata: Metadata = {
  title: "Executive Assistant",
  description: "Executive Assistant Agent - calendar, mail triage and approvals",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full flex flex-col md:flex-row">
        <aside className="border-b p-4 md:w-56 md:border-b-0 md:border-r">
          <h1 className="mb-3 font-semibold">Executive Assistant</h1>
          <Nav />
        </aside>
        <main className="flex-1 p-6">{children}</main>
      </body>
    </html>
  );
}
