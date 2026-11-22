/** Evidence-backed hypotheses for the family ingredient research queue.
 * Retrieval: 2026-11-22. Never use as an automatic replacement or clinical
 * per-serving certification; the label and attendee restrictions must be reviewed.
 */
export type ResearchSuggestion = {
  key: string;
  match: RegExp;
  replacement: string;
  brand: string;
  retailer: string;
  retailerUrl: string | null;
  declaredIngredients: string | null;
  monashUrl: string;
  reason: string;
  servingEvidence: string;
};

const MONASH_AROMATICS = "https://www.monashfodmap.com/blog/cooking-with-onion-and-garlic-myths-and/";
const MONASH_OIL = "https://www.monashfodmap.com/blog/all-about-onion-garlic-and-infused-oils-on-the-low-fodmap-diet/";
const MONASH_FOOD_LIST = "https://www.monashfodmap.com/about-fodmap-and-ibs/high-and-low-fodmap-foods/";
const MONASH_LEGUMES = "https://www.monashfodmap.com/about-fodmap-and-ibs/frequently-asked-questions/";
const MONASH_GRAINS = "https://monashfodmap.com/blog/gluten-and-ibs/";

const references: ResearchSuggestion[] = [
  {
    key: "allium:leek",
    match: /alho franc[eê]s/i,
    replacement: "Parte verde do alho-francês / cebolinho fresco",
    brand: "Auchan",
    retailer: "Auchan",
    retailerUrl: "https://www.auchan.pt/pt/produtos-frescos/legumes/ervas-aromaticas/cebolinho-auchan-25-g/3372574.html",
    declaredIngredients: "Cebolinho fresco (produto hortícola; confirmar etiqueta recebida).",
    monashUrl: MONASH_AROMATICS,
    reason: "A parte branca do alho-francês concentra frutanos; usar apenas a parte verde indicada pela fonte. Cebolinho é uma alternativa aromática, não uma troca de peso equivalente.",
    servingEvidence: "Sem limite quantitativo certificado para este produto; validar porção na aplicação Monash.",
  },
  {
    key: "allium:spring-onion",
    match: /cebolinhas?/i,
    replacement: "Parte verde de cebolinha / cebolinho fresco",
    brand: "Auchan",
    retailer: "Auchan",
    retailerUrl: "https://www.auchan.pt/pt/produtos-frescos/legumes/ervas-aromaticas/cebolinho-auchan-25-g/3372574.html",
    declaredIngredients: "Cebolinho fresco; verificar se a receita original usa a parte branca das cebolinhas.",
    monashUrl: MONASH_AROMATICS,
    reason: "A proposta só envolve as partes verdes; cebolinhas pérola inteiras não se tornam adequadas por cozinhar sem as comer.",
    servingEvidence: "Confirmar porção por pessoa na aplicação Monash.",
  },
  {
    key: "allium:garlic",
    match: /alho/i,
    replacement: "Azeite aromatizado com alho, sem pedaços sólidos de alho",
    brand: "Preparação caseira / produto de azeite infundido por verificar",
    retailer: "Preparação culinária",
    retailerUrl: null,
    declaredIngredients: "Azeite e alho apenas para aromatização; não manter sólidos de alho no prato.",
    monashUrl: MONASH_OIL,
    reason: "Os frutanos são solúveis em água e não em óleo. Não substituir alho em unidades/gramas por igual peso de azeite. Preparar e conservar o óleo com segurança alimentar.",
    servingEvidence: "Porção de óleo, gordura total e composição da refeição requerem nova avaliação.",
  },
  {
    key: "allium:onion",
    match: /cebola/i,
    replacement: "Cebolinho fresco ou parte verde de cebolinha",
    brand: "Auchan",
    retailer: "Auchan",
    retailerUrl: "https://www.auchan.pt/pt/produtos-frescos/legumes/ervas-aromaticas/cebolinho-auchan-25-g/3372574.html",
    declaredIngredients: "Cebolinho fresco; confirmar rotulagem/identificação no produto recebido.",
    monashUrl: MONASH_AROMATICS,
    reason: "Substituição aromática, não equivalência de volume. Para engrossar refogados, usar outro vegetal permitido em quantidade a avaliar.",
    servingEvidence: "Confirmar porção e dose da receita toda; sem limite por dose deste produto.",
  },
  {
    key: "dairy:greek-yoghurt",
    match: /iogurte grego/i,
    replacement: "Iogurte grego natural sem lactose Mevgal",
    brand: "Mevgal",
    retailer: "Auchan",
    retailerUrl: "https://www.auchan.pt/pt/alimentacao/produtos-lacteos/iogurtes/cremosos-gregos/iogurte-mevgal-sem-lactose-grego-natural-2-150g/2222439.html",
    declaredIngredients: "Leite de vaca parcialmente desnatado, proteína do leite, culturas de iogurte, lactase (informação comercial publicada).",
    monashUrl: MONASH_FOOD_LIST,
    reason: "Alternativa sem lactose; mantém proteínas do leite, não serve para alergia ao leite. Verificar rótulo, porção e adequação individual.",
    servingEvidence: "Embalagem de 150 g; embalagem não equivale a uma porção Monash certificada.",
  },
  {
    key: "dairy:yoghurt",
    match: /iogurte/i,
    replacement: "Iogurte natural magro sem lactose Auchan",
    brand: "Auchan",
    retailer: "Auchan",
    retailerUrl: "https://www.auchan.pt/pt/alimentacao/produtos-lacteos/sem-lactose/iogurte-sem-lactose/iogurte-natural-magro-auchan-sem-lactose-4x125g/3921275.html",
    declaredIngredients: null,
    monashUrl: MONASH_FOOD_LIST,
    reason: "Candidato sem lactose; não isento de proteína de leite. Confirmar rótulo atual e quaisquer aditivos ricos em FODMAP.",
    servingEvidence: "Unidades de 125 g; validar a porção do plano para cada participante.",
  },
  {
    key: "dairy:milk",
    match: /leite/i,
    replacement: "Leite meio-gordo sem lactose Mimosa",
    brand: "Mimosa",
    retailer: "Continente",
    retailerUrl: "https://www.continente.pt/produto/o-mesmo-sabor-sem-lactose-foodmimosalactose.html",
    declaredIngredients: null,
    monashUrl: MONASH_FOOD_LIST,
    reason: "Alternativa sem lactose, sem remover a proteína do leite; verificar composição completa e porções. Preparações 'qb' não têm dose utilizável.",
    servingEvidence: "Limite por pessoa não extraído do app Monash; 180/200/500/800 ml da receita não são doses certificadas.",
  },
  {
    key: "grain:spaghetti",
    match: /esparguete|fettuccine|fetucine/i,
    replacement: "Massa esparguete sem glúten Rummo, arroz e milho",
    brand: "Rummo",
    retailer: "Auchan / Continente",
    retailerUrl: "https://www.auchan.pt/pt/biologicos-e-alternativas/sem-gluten/mercearia-sem-gluten/massas-e-farinhas-sem-gluten/massa-rummo-spaguetti-sem-gluten-400g/3240169.html",
    declaredIngredients: "Arroz integral 36%, milho amarelo 32%, milho branco 20%, arroz 8%, fécula de batata 3%, emulsionante vegetal; verificar rótulo atual.",
    monashUrl: MONASH_GRAINS,
    reason: "Alternativa de cereal. Sem glúten não equivale a baixo FODMAP e a receita completa tem de ser revista.",
    servingEvidence: "Dose cozida por pessoa deve ser avaliada; embalagem de 400 g não representa dose.",
  },
  {
    key: "grain:short-pasta",
    match: /macarronete|macarrão|massa cotovelos/i,
    replacement: "Massa Auchan cotovelos ou fusilli sem glúten, milho e arroz",
    brand: "Auchan",
    retailer: "Auchan",
    retailerUrl: "https://www.auchan.pt/pt/biologicos-e-alternativas/sem-gluten/mercearia-sem-gluten/massas-e-farinhas-sem-gluten/massa-auchan-cotovelos-sem-gluten-500g/2749325.html",
    declaredIngredients: "Farinha de milho branco 65%, farinha de milho amarelo 29,7%, farinha de arroz 5%, emulsionante (rótulo publicado).",
    monashUrl: MONASH_GRAINS,
    reason: "Alternativa de formato equivalente; conversão de 'emb' para gramas exige peso original, rendimento e dose por pessoa.",
    servingEvidence: "Dose da massa cozida por pessoa por validar na fonte Monash.",
  },
  {
    key: "grain:muesli",
    match: /muesli/i,
    replacement: "Flocos de milho sem glúten Verival, sem açúcar adicionado",
    brand: "Verival",
    retailer: "Continente",
    retailerUrl: "https://www.continente.pt/produto/cereais-corn-flakes-sem-gluten-verival-5779336.html",
    declaredIngredients: "Flocos de milho biológicos; confirmar lista completa de ingredientes e eventuais aditivos no rótulo.",
    monashUrl: MONASH_GRAINS,
    reason: "Alternativa aos mueslis com trigo/frutos secos ricos em FODMAP; não conserva necessariamente o mesmo perfil nutricional de fibra.",
    servingEvidence: "Rever porção e açúcares do produto efetivamente comprado.",
  },
  {
    key: "vegetable:mushrooms",
    match: /cogumelos/i,
    replacement: "Cogumelos comuns laminados em conserva Auchan, escorridos",
    brand: "Auchan",
    retailer: "Auchan",
    retailerUrl: "https://www.auchan.pt/pt/alimentacao/mercearia/conservas/cogumelo-milho-ervilha-feijao-e-outros/cogumelos-laminados-auchan-3x200%28115%29g/3903247.html",
    declaredIngredients: "Cogumelos comuns, água, sal, ácido cítrico (rótulo publicado).",
    monashUrl: "https://www.monashfodmap.com/recipe/hot-sour-asian-soup/",
    reason: "Monash distingue cogumelos comuns frescos de cogumelos comuns em conserva/salmoura; escorrer a água e confirmar a porção.",
    servingEvidence: "115 g peso escorrido por unidade da embalagem; não é limite low FODMAP.",
  },
  {
    key: "fruit:apple",
    match: /maçã/i,
    replacement: "Kiwi verde, laranja ou morangos frescos",
    brand: "Hortofrutícolas frescos, marca à escolha",
    retailer: "Auchan / Continente",
    retailerUrl: null,
    declaredIngredients: "Fruta fresca sem aditivos, confirmar o produto e o estado de maturação.",
    monashUrl: MONASH_FOOD_LIST,
    reason: "A maçã contém FODMAPs relevantes; escolher fruta com perfil mais favorável, ajustando sabor e peso à receita.",
    servingEvidence: "A dose deve ser confirmada na aplicação Monash para cada fruta; não pressupor equivalência de 100–150 g.",
  },
  {
    key: "legume:beans",
    match: /feijão vermelho|grão(?:-de-bico| de bico)?/i,
    replacement: "Grão-de-bico cozido em conserva Auchan, escorrido e passado por água",
    brand: "Auchan",
    retailer: "Auchan",
    retailerUrl: "https://www.auchan.pt/pt/alimentacao/mercearia/conservas/cogumelo-milho-ervilha-feijao-e-outros/grao-de-bico-auchan-cozido-820%28520%29g/640416.html",
    declaredIngredients: "Grão-de-bico cozido, água, sal (rótulo publicado).",
    monashUrl: MONASH_LEGUMES,
    reason: "Conserva escorrida/lavada pode permitir porções pequenas; NÃO equivale a trocar livremente 2–3 embalagens de feijão ou grão.",
    servingEvidence: "Verificar o limite para grão-de-bico escorrido na app Monash e reduzir dose, ou substituir parte por outra proteína.",
  },
];

export function researchSuggestionsForIngredient(name: string): ResearchSuggestion[] {
  return references.filter(row => row.match.test(name)).slice(0, 2);
}

export const RESEARCH_REFERENCE_DATE = "2026-11-22";
