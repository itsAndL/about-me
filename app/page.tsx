import { contactLinks, projects, sourceUrl } from "./content";

function NewTabNote() {
  return <span className="visually-hidden"> (opens in a new tab)</span>;
}

const newTab = { target: "_blank", rel: "noopener noreferrer" } as const;

const personJsonLd = {
  "@context": "https://schema.org",
  "@type": "Person",
  name: "Ayoub Lkebch",
  jobTitle: "Full-stack product engineer",
  address: { "@type": "PostalAddress", addressLocality: "Casablanca", addressCountry: "MA" },
  url: "https://itsandl.github.io/about-me/",
  email: "mailto:ayoub003lkebch@gmail.com",
  sameAs: ["https://www.linkedin.com/in/ayoublkebch", "https://github.com/itsAndL", "https://ayoublkebch.com"],
};

export default function Home() {
  return (
    <>
      <script
        type="application/ld+json"
        // Escape "<" so the JSON can never close the script element early.
        dangerouslySetInnerHTML={{ __html: JSON.stringify(personJsonLd).replace(/</g, "\\u003c") }}
      />
      <header className="site-header">
        <span className="monogram">AL</span>
      </header>

      <main id="main">
        <div className="intro">
          <h1>Ayoub Lkebch</h1>
          <p className="lede">
            Full-stack product engineer. I build software for businesses — <strong>4 B2B products shipped</strong>,
            now building <strong>Opilote</strong>.
          </p>
          <p className="ai-note">
            I work with AI coding agents every day: I write the spec, review every diff, and ship small PRs.
          </p>
          <p className="location">Casablanca, Morocco</p>
        </div>

        <section className="projects" aria-labelledby="shipped-heading">
          <h2 id="shipped-heading">Shipped</h2>
          <ul>
            {projects.map((project) => (
              <li className="project" key={project.url}>
                {/* One text node per string: adjacent JSX expressions would render a <!-- --> separator. */}
                <h3 className="project-name">
                  {project.badge ? `${project.name} ` : project.name}
                  {project.badge && <span className="badge">{project.badge}</span>}
                </h3>
                <a className="project-link" href={project.url} {...newTab}>
                  {`${project.domain} `}
                  <span aria-hidden="true">↗</span>
                  <NewTabNote />
                </a>
                <p className="project-desc">{project.description}</p>
              </li>
            ))}
          </ul>
        </section>

        <section className="contact" aria-labelledby="contact-heading">
          <h2 id="contact-heading">Contact</h2>
          <ul>
            {contactLinks.map((link) =>
              link.href.startsWith("mailto:") ? (
                <li key={link.href}>
                  <a className="contact-link" href={link.href}>
                    {link.label}
                  </a>
                </li>
              ) : (
                <li key={link.href}>
                  <a className="contact-link" href={link.href} {...newTab}>
                    {link.label}
                    <NewTabNote />
                  </a>
                </li>
              ),
            )}
          </ul>
        </section>
      </main>

      <footer className="site-footer">
        <p>
          {"© 2026 Ayoub Lkebch · Built with Fredrin · "}
          <a href={sourceUrl} {...newTab}>
            Source on GitHub
            <NewTabNote />
          </a>
        </p>
      </footer>
    </>
  );
}
