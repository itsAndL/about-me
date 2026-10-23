import type { Metadata } from "next";
import "./globals.css";

// Full SEO/social metadata lands in the metadata ticket.
export const metadata: Metadata = {
  title: "Ayoub Lkebch — Full-stack product engineer",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <a className="visually-hidden-focusable" href="#main">
          Skip to content
        </a>
        {children}
      </body>
    </html>
  );
}
