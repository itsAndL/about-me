import Link from "next/link";

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
