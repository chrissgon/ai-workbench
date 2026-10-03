export interface DocPage {
  file: string;
  section: string;
  slug: string;
  title?: string;
  description?: string;
}

const SLUG = /^[a-z0-9]+(-[a-z0-9]+)*$/;

// Returns one message per broken rule, each starting with the file it concerns; an empty list means valid.
export function validateDocs(pages: DocPage[]): string[] {
  const errors: string[] = [];
  const seen = new Map<string, string>();
  for (const page of pages) {
    if (page.title === undefined || page.title.trim() === "") {
      errors.push(`${page.file}: title is missing`);
    }
    if (!SLUG.test(page.slug)) {
      errors.push(`${page.file}: slug "${page.slug}" must be lowercase letters, digits and single hyphens`);
    }
    if (page.description !== undefined && page.description.length > 160) {
      errors.push(`${page.file}: description is longer than 160 characters`);
    }
    const address = page.slug;
    const first = seen.get(address);
    if (first !== undefined) {
      errors.push(`${page.file}: address /${address} is already used by ${first}`);
    } else {
      seen.set(address, page.file);
    }
  }
  return errors;
}
