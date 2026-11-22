import type { ReviewRecipe } from "./api/dietaryReviewClient";

export type AIResearchDraft = {
  recipe_id: string;
  ingredient_id: string;
  replacement_name: string;
  evidence_url: string;
  retailer_url?: string;
  notes: string;
  proposed_quantity?: string;
  proposed_unit?: string;
  evidence_status: "unverified";
};

export type AIEngineeringChange = {
  kind: "algorithm" | "application_code" | "reference_catalogue";
  summary: string;
  target_paths: string[];
  rationale: string;
  acceptance_tests: string[];
};

export type AIResearchImport = {
  schema_version: "nutriflow.ai-review.v1";
  suggestions: AIResearchDraft[];
  engineering_changes?: AIEngineeringChange[];
};

export function readEngineeringChanges(raw: string): AIEngineeringChange[] {
  if (raw.length > 200_000) throw Error("Ficheiro JSON demasiado grande.");
  const value: unknown = JSON.parse(raw);
  if (!value || typeof value !== "object" || Array.isArray(value)) throw Error("JSON inválido.");
  const doc = value as Record<string, unknown>;
  if (doc.schema_version !== "nutriflow.ai-review.v1") throw Error("Versão não suportada.");
  if (doc.engineering_changes === undefined) return [];
  if (!Array.isArray(doc.engineering_changes) || doc.engineering_changes.length > 20)
    throw Error("Lista engineering_changes inválida (máximo 20).");
  return doc.engineering_changes.map((entry, index) => {
    if (!entry || typeof entry !== "object" || Array.isArray(entry))
      throw Error(`Alteração de código ${index + 1} inválida.`);
    const row = entry as Record<string, unknown>;
    if (!["algorithm", "application_code", "reference_catalogue"].includes(String(row.kind)) ||
        typeof row.summary !== "string" || !row.summary.trim() || row.summary.length > 300 ||
        typeof row.rationale !== "string" || row.rationale.length > 1500 ||
        !Array.isArray(row.target_paths) || row.target_paths.length > 12 ||
        !row.target_paths.every(p => typeof p === "string" && p.length < 200 &&
          /^(apps\/|packages\/|docs\/|database\/)/.test(p) && !p.includes("..") && !p.includes("\\")) ||
        !Array.isArray(row.acceptance_tests) || row.acceptance_tests.length > 20 ||
        !row.acceptance_tests.every(t => typeof t === "string" && t.length <= 400)) {
      throw Error(`Alteração de código ${index + 1}: campos ou caminhos inválidos.`);
    }
    return {
      kind: row.kind as AIEngineeringChange["kind"],
      summary: row.summary,
      target_paths: row.target_paths as string[],
      rationale: row.rationale,
      acceptance_tests: row.acceptance_tests as string[],
    };
  });
}

export function buildGitHandoff(changes: AIEngineeringChange[]): string {
  return [
    "NutriFlow AI v2 — instruções para implementação e replicação no GitHub.",
    "Repositório: lfloureiro/nutriflow-ai-v2",
    "Branch de trabalho: codex/ux-drawer-next-batch-20261119 (PR #76 ou sucessora documentada).",
    "Estas alterações NÃO devem ser executadas diretamente a partir do JSON importado.",
    "Rever cada pedido, confirmar os ficheiros reais, implementar em código-fonte,",
    "escrever testes, correr Web CI/API CI/UX E2E e criar commits na branch correspondente.",
    "Não publicar dados pessoais/familiares, segredos, histórias clínicas ou conteúdos da DB.",
    "Não fazer merge automático nem relaxar restrições alimentares.",
    "",
    ...changes.flatMap((change, index) => [
      `${index + 1}. [${change.kind}] ${change.summary}`,
      `   Ficheiros sugeridos: ${change.target_paths.join(", ") || "identificar no repositório"}`,
      `   Razão: ${change.rationale}`,
      `   Aceitação: ${change.acceptance_tests.join(" | ") || "acrescentar testes"}`,
    ]),
  ].join("\n");
}

export type AIResearchPreviewRow = AIResearchDraft & {
  recipeName: string;
  ingredientName: string;
  issue?: string;
};

const safeHttps = (value: string) => {
  try {
    const url = new URL(value);
    const host = url.hostname.toLowerCase();
    const placeholder = ["localhost", "127.0.0.1", "::1"].includes(host) ||
      [".example", ".invalid", ".test", ".localhost", ".local"].some(suffix => host.endsWith(suffix));
    return url.protocol === "https:" && !url.username && !url.password && !placeholder;
  } catch {
    return false;
  }
};

export function buildAIResearchExport(recipes: ReviewRecipe[], excluded: string[]): string {
  const relevant = new Set(excluded);
  return JSON.stringify({
    schema_version: "nutriflow.ai-review.v1",
    task: "Find evidence-based ingredient replacement candidates for the family's recipes. Return JSON matching schema_version, suggestions[]. Never claim clinical approval.",
    safety: "All substitutions are unverified, require label, portion and per-person review; do not mutate recipes, diets, meal plans or shopping lists.",
    ingredients: recipes.flatMap(recipe =>
      recipe.ingredients.filter(row => relevant.has(row.food_item_id)).map(row => ({
        recipe_id: recipe.id,
        recipe_name: recipe.name,
        ingredient_id: row.id,
        ingredient_name: row.name,
        original_quantity: row.quantity,
        original_unit: row.unit,
        existing_proposals: row.substitutions.filter(s => s.status !== "rejected").map(s => s.replacement_name),
      })),
    ),
    git_policy: {
      family_data: "Ingredient/recipe proposals are DB-only; never commit household records to Git.",
      algorithm_or_code: "If a suggestion requires changing algorithm, application code or reusable seed/migration, include an engineering_changes record and prepare a reviewed change in GitHub branch codex/ux-drawer-next-batch-20261119. Do not execute code from this JSON or commit automatically.",
      testing: "Tests + CI before PR; no automatic merge. Remove all personal/family data from the issue/commit.",
    },
    output_example: {
      schema_version: "nutriflow.ai-review.v1",
      suggestions: [{
        recipe_id: "copy a real recipe_id from ingredients",
        ingredient_id: "copy the corresponding ingredient_id",
        replacement_name: "specific proposed alternative",
        evidence_url: "https://official-source.example/reference",
        retailer_url: "https://shop.example/product",
        notes: "Evidence, published ingredients, date checked, uncertainty and portion to validate.",
        evidence_status: "unverified",
      }],
      engineering_changes: [{
        kind: "algorithm",
        summary: "Description of proposed algorithm improvement, only when needed",
        target_paths: ["apps/api/app/services/"],
        rationale: "Explain why this cannot be handled by family DB data alone",
        acceptance_tests: ["Synthetic regression test"],
      }],
    },
  }, null, 2);
}

export function previewAIResearchImport(raw: string, recipes: ReviewRecipe[]): AIResearchPreviewRow[] {
  if (raw.length > 200_000) throw Error("Ficheiro JSON demasiado grande (máximo 200 KB).");
  let value: unknown;
  try { value = JSON.parse(raw); } catch { throw Error("JSON inválido."); }
  if (!value || typeof value !== "object" || Array.isArray(value)) throw Error("É necessário um objeto JSON.");
  const document = value as Record<string, unknown>;
  if (document.schema_version !== "nutriflow.ai-review.v1") throw Error("Versão do formato de importação não suportada.");
  if (!Array.isArray(document.suggestions) || document.suggestions.length > 200) throw Error("A lista suggestions é obrigatória (até 200).");
  readEngineeringChanges(raw); // Reject malformed engineering requests even if substitutions are valid.
  const ingredientById = new Map(recipes.flatMap(recipe => recipe.ingredients.map(ingredient => [
    ingredient.id, {recipe, ingredient},
  ] as const)));
  const seen = new Set<string>();
  return document.suggestions.map((candidate, index) => {
    if (!candidate || typeof candidate !== "object" || Array.isArray(candidate)) throw Error(`Proposta ${index + 1} inválida.`);
    const row = candidate as Record<string, unknown>;
    const recipeId = row.recipe_id;
    const ingredientId = row.ingredient_id;
    const name = row.replacement_name;
    const notes = row.notes;
    const evidence = row.evidence_url;
    if (typeof recipeId !== "string" || typeof ingredientId !== "string" || typeof name !== "string" ||
        typeof notes !== "string" || typeof evidence !== "string" || row.evidence_status !== "unverified" ||
        name.trim().length < 2 || name.length > 160 || notes.length > 5000 ||
        !safeHttps(evidence) ||
        (row.retailer_url !== undefined && (typeof row.retailer_url !== "string" || !safeHttps(row.retailer_url)))) {
      throw Error(`Proposta ${index + 1}: campos, evidência HTTPS ou estado inválidos.`);
    }
    const original = ingredientById.get(ingredientId);
    if (!original || original.recipe.id !== recipeId) throw Error(`Proposta ${index + 1}: receita ou ingrediente não pertence à família.`);
    const quantity = row.proposed_quantity;
    const unit = row.proposed_unit;
    if ((quantity !== undefined || unit !== undefined) &&
        (typeof quantity !== "string" || typeof unit !== "string" ||
         !/^\d+(?:[.,]\d+)?$/.test(quantity) || Number(quantity.replace(",", ".")) <= 0 ||
         unit.trim().length === 0 || unit.length > 24)) {
      throw Error(`Proposta ${index + 1}: quantidade e unidade precisam de revisão conjunta.`);
    }
    const duplicateKey = `${ingredientId}:${name.trim().toLocaleLowerCase()}`;
    const existing = original.ingredient.substitutions.some(s =>
      s.status !== "rejected" && s.replacement_name.trim().toLocaleLowerCase() === name.trim().toLocaleLowerCase());
    const repeated = seen.has(duplicateKey);
    seen.add(duplicateKey);
    return {
      recipe_id: recipeId,
      ingredient_id: ingredientId,
      replacement_name: name.trim(),
      evidence_url: evidence,
      ...(typeof row.retailer_url === "string" ? {retailer_url: row.retailer_url} : {}),
      notes,
      ...(typeof quantity === "string" && typeof unit === "string"
        ? {proposed_quantity: quantity, proposed_unit: unit} : {}),
      evidence_status: "unverified" as const,
      recipeName: original.recipe.name,
      ingredientName: original.ingredient.name,
      ...(existing || repeated ? {issue: "Proposta já registada ou repetida no ficheiro."} : {}),
    };
  });
}
