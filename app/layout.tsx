import type { Metadata, Viewport } from "next";
import "./globals.css";

const title = "Ayoub Lkebch — Full-stack product engineer";
const description =
  "Ayoub Lkebch — full-stack product engineer in Casablanca, Morocco. 4 B2B products shipped; now building Opilote, a GPS fleet-management SaaS.";

// Icons and the share image come from the app/ file conventions (icon.svg, icon.ico,
// apple-icon.png, opengraph-image.png, twitter-image.png + their .alt.txt files).
export const metadata: Metadata = {
  metadataBase: new URL("https://itsandl.github.io"),
  title,
  description,
  alternates: { canonical: "/about-me/" },
  openGraph: { type: "website", url: "/about-me/", title, description, locale: "en_US" },
  twitter: { card: "summary_large_image", title, description },
  robots: { index: true, follow: true },
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#fbfaf7" },
    { media: "(prefers-color-scheme: dark)", color: "#111312" },
  ],
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
