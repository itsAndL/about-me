import type { Metadata } from "next";
import Link from "next/link";

// The root layout marks the home page indexable and canonical; a 404 must be neither.
export const metadata: Metadata = {
  robots: { index: false, follow: true },
  alternates: { canonical: null },
};

// Exported as out/404.html, which GitHub Pages serves for unknown paths under /about-me/.
export default function NotFound() {
  return (
    <>
      <header className="site-header">
        <span className="monogram">AL</span>
      </header>

      <main id="main">
        <div className="intro">
          <h1>Page not found</h1>
          <p className="lede">There is nothing at this address.</p>
          <p>
            <Link href="/">Back to Ayoub Lkebch</Link>
          </p>
        </div>
      </main>
    </>
  );
}
