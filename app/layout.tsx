import type { Metadata } from "next";
import "./globals.css";

// Full SEO/social metadata lands in the metadata ticket.
export const metadata: Metadata = {
  title: "Ayoub Lkebch — Full-stack product engineer",
};

// Runs while <head> parses, before first paint: a stored theme choice beats the system one.
const themeScript = `(function(){try{var t=localStorage.getItem("theme");if(t==="dark"||t==="light")document.documentElement.dataset.theme=t}catch(e){}})()`;

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    // The head script sets data-theme before React hydrates.
    <html lang="en" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>
      <body>
        <a className="visually-hidden-focusable" href="#main">
          Skip to content
        </a>
        {children}
      </body>
    </html>
  );
}
