/**
 * Curated, source-attributed artwork for the next meal.
 *
 * A picture is never chosen from unrelated keywords or from the meal type.
 * Item/recipe media always takes priority; the catalog is explicitly keyed
 * to known culinary labels. The title itself never triggers a live web query.
 */
export type MealHeroImage = {
  src: string;
  alt: string;
  source: string | null;
  author: string | null;
  license: string | null;
  kind: "meal" | "proposal" | "catalog";
};

type DirectMedia = { image_url?: string | null; hero_image_url?: string | null };
type MealItem = DirectMedia & { recipe_name?: string | null; title?: string | null };
type ProposalItem = DirectMedia & { candidate_name?: string | null };

type CuratedPhoto = {
  filename: string;
  subject: string;
  author: string;
  license: string;
};

const CURATED: Record<string, CuratedPhoto> = {
  "frango rapido": {
    filename: "Liat Portal for Foodie Disorder - Roasted chicken with vegetables and white rice.jpg",
    subject: "Frango cozinhado com legumes e arroz (fotografia ilustrativa)",
    author: "HaJunkiyada",
    license: "CC BY-SA 4.0",
  },
  "salmao no forno com ervinhas da provenca": {
    filename: "Liat Portal for Foodie Disorder - Salmon with garlic and herbs, crushed potatoes and peas.jpg",
    subject: "Salmão com ervas, batatas e ervilhas (fotografia ilustrativa)",
    author: "HaJunkiyada",
    license: "CC BY-SA 4.0",
  },
  "salmao no forno com ervas": {
    filename: "Liat Portal for Foodie Disorder - Salmon with garlic and herbs, crushed potatoes and peas.jpg",
    subject: "Salmão com ervas, batatas e ervilhas (fotografia ilustrativa)",
    author: "HaJunkiyada",
    license: "CC BY-SA 4.0",
  },
  "salmao batata e cenoura": {
    filename: "Liat Portal for Foodie Disorder - Salmon with garlic and herbs, crushed potatoes and peas.jpg",
    subject: "Salmão com batatas e legumes (fotografia ilustrativa)",
    author: "HaJunkiyada",
    license: "CC BY-SA 4.0",
  },
  "banana e frutos secos": {
    filename: "Liat Portal for Foodie Disorder - Banana Mango Nut Bowl.jpg",
    subject: "Banana com fruta e frutos secos (fotografia ilustrativa)",
    author: "HaJunkiyada",
    license: "CC BY-SA 4.0",
  },
  "torrada com queijo": {
    filename: "Cheese on toast hi res.jpg",
    subject: "Torrada com queijo",
    author: "Zorin90",
    license: "CC BY-SA 4.0",
  },
  "pao queijo e tomate": {
    filename: "Toast with cheddar cheese and tomato.jpg",
    subject: "Torrada com queijo e tomate",
    author: "OKJaguar",
    license: "CC0 1.0",
  },
};

export function normalizeMealImageName(value: string | null | undefined): string {
  return (value ?? "")
    .normalize("NFD").replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/\s*[·–—-]\s*familia\s*$/i, "")
    .replace(/\s*(?:\(|\[)(?:planeada|adaptacao aplicada)(?:\)|\])\s*$/i, "")
    .replace(/[^a-z0-9]+/g, " ")
    .trim().replace(/\s+/g, " ");
}

function safeImageURL(input: string | null | undefined): string | null {
  if (!input) return null;
  const src = input.trim();
  if (src.startsWith("/") && !src.startsWith("//")) return src;
  try {
    const url = new URL(src);
    return url.protocol === "https:" ? url.href : null;
  } catch {
    return null;
  }
}

function curated(name: string | null): MealHeroImage | null {
  const match = CURATED[normalizeMealImageName(name)];
  if (!match) return null;
  const path = encodeURIComponent(match.filename);
  return {
    src: `https://commons.wikimedia.org/wiki/Special:FilePath/${path}?width=900`,
    alt: match.subject,
    source: `https://commons.wikimedia.org/wiki/File:${match.filename.replace(/ /g, "_")}`,
    author: match.author,
    license: match.license,
    kind: "catalog",
  };
}

export function resolveMealHeroImage({
  planned, proposal, recipeImageUrl,
}: {
  planned?: MealItem | null;
  proposal?: ProposalItem | null;
  recipeImageUrl?: string | null;
}): MealHeroImage | null {
  // Same object owns both the hero headline and image decision.
  const item = planned ?? proposal ?? null;
  if (!item) return null;
  const direct = safeImageURL(item.hero_image_url) ?? safeImageURL(item.image_url) ??
    safeImageURL(recipeImageUrl);
  const title = planned ? (planned.recipe_name ?? planned.title) : (proposal?.candidate_name ?? null);
  if (direct) return {
    src: direct,
    alt: title ?? "Fotografia da refeição",
    source: null,
    author: null,
    license: null,
    kind: planned ? "meal" : "proposal",
  };
  return curated(title);
}
