// Page copy, kept verbatim from the approved design. Edit text here, not in the markup.

export type Project = {
  name: string;
  url: string;
  /** Bare domain shown as the link text. */
  domain: string;
  description: string;
  /** Only the product being built right now carries a badge. */
  badge?: string;
};

export type ContactLink = {
  href: string;
  label: string;
  /** Phone label, shown instead of `label` at ≤520px. */
  shortLabel?: string;
  /** Accessible name carrying the full value; set wherever `shortLabel` is. */
  ariaLabel?: string;
  /** Decorative glyph shown before the long label. */
  icon?: string;
};

export const projects: Project[] = [
  {
    name: "Opilote",
    url: "https://opilote.com",
    domain: "opilote.com",
    description:
      "GPS fleet-management SaaS I'm building end to end: Rails API, React web app, React Native app live on Google Play.",
    badge: "Building now",
  },
  {
    name: "Timlead",
    url: "https://getstarted.timlead.com",
    domain: "getstarted.timlead.com",
    description: "Field-service platform used by 6,000+ people. I built its AI assistant and MCP server.",
  },
  {
    name: "TestSkills",
    url: "https://testskills.app",
    domain: "testskills.app",
    description: "Skills-assessment and hiring platform I led from the first commit.",
  },
  {
    name: "Humaneo",
    url: "https://humaneo.ma",
    domain: "humaneo.ma",
    description: "HR SaaS used by 7,000+ employees.",
  },
];

// The mailto link opens in the same tab; every other link opens a new one.
export const contactLinks: ContactLink[] = [
  {
    href: "mailto:lkebch.ayoub@gmail.com",
    label: "lkebch.ayoub@gmail.com",
    shortLabel: "Email",
    ariaLabel: "Email lkebch.ayoub@gmail.com",
    icon: "✉",
  },
  { href: "https://www.linkedin.com/in/ayoublkebch", label: "LinkedIn" },
  { href: "https://github.com/itsAndL", label: "GitHub" },
  {
    href: "https://ayoublkebch.com",
    label: "ayoublkebch.com",
    shortLabel: "Website",
    ariaLabel: "Website ayoublkebch.com",
  },
];

export const sourceUrl = "https://github.com/itsAndL/about-me";
