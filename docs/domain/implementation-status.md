## Auditoria, publicação e retalho — 18/10/2026

Consolidação publicada na branch v2, com CI API/Web bem-sucedido; sem merge.
Catálogo passa a onze produtos observados Continente/Auchan, sete novos importados
idempotentemente sem alterar receitas. Evidência distingue descrição, ingredientes e
nutrição; zeros suspeitos da farinha não se tornam composição. Compras carregadas à
abertura, com nomes acessíveis. Inventário completo do esquema e prioridades em
`technical-audit-2026-10-18.md` e `schema-audit-2026-10-18.md`.

## Início, semanas guardadas e alternativas na linha — ADR-066 (18/10/2026)

Implementado bloco de consulta de semanas no início, com datas, navegação e cartões das
refeições realmente guardadas. Cada cartão inclui as suas alternativas; abrir leva à semana
correta. Menu Plano abre agenda semanal. Data consultada separada de hoje e preservada
para voltar ao início sem perder a semana aberta.

Agenda semanal/diária e detalhe mantêm trocas visíveis; variantes/transformações aplicadas
prevalecem sobre propostas. Revisão de ingredientes e compras mostram ingrediente →
alternativa na mesma linha. Compras usam só propostas das receitas do intervalo guardado,
não assumem quantidades equivalentes nem mudam os itens comprados. Botão de supermercado
só aparece quando há produtos correspondentes, evitando detalhes vazios.

118 testes frontend, TypeScript/build e diff check passaram. Interface real confirmou:
início → próxima semana (7 refeições) → agenda de 19/10 → escalopes com trocas visíveis;
revisão com cabeçalho ingrediente/alternativa e compras com alternativas diretas. Nenhuma
refeição/quantidade foi alterada. Sem migration ou alteração backend neste incremento.

Vite Windows passou a polling: havia módulos antigos em cache apesar de ficheiros alterados.
Servidor atual Vite 5173 sessão 79136; API 8000 sessão 95485. Sem commit/push.
Evidência: `docs/audits/2026-10-18/home-saved-weeks-alternatives.png` e
`docs/audits/2026-10-18/shopping-inline-alternatives.png`.

## Seleção do prato e almoços — 18/10/2026 (ADR-065)

Corrigido o problema reportado no PDF do utilizador: o detalhe mostra só propostas do prato
selecionado (incluindo ingredientes com proposta mas sem referência alta FODMAP) e as
operações realmente aplicadas de variantes completas. Catálogo global removido do percurso.
Revisão de ingredientes limitada a prato/data/tempo/presentes, com regras refrescadas pelo
servidor mesmo para um almoço que não estava na lista de tempos a gerar.

Origem por tipo de refeição guardada em `FamilyWeekSetup.settings.meal_sources`, sem
migration. Almoços sugerem entrega, com escolha casa/restaurante. Sem prato elegível, ficam
pendentes. Detalhe reúne plataformas e restaurantes, sem guardar/encomendar automaticamente.
Conta normal de cliente confirmada pelo utilizador: nenhum acesso API consumer nem adaptador
live; links funcionais não significam importação. Catálogo real de Uber/Glovo/Bolt pendente.

OpenStreetMap: corrigido timeout HTTP inferior ao da query, recuperação de falhas temporárias,
respeito por HTTP 4xx/429 e fallback Nominatim limitado à zona, identificado como seleção de
correspondências, com cache curta e sem avaliações/nutrição inventadas. Teste direto real
obteve 12 restaurantes em Lisboa; interface final confirmada: 12 resultados, mapa incorporado e seleção sincronizada.

Validação: execução completa API 386 passou antes da extensão Nominatim; 14 testes de
restaurantes/capacidades passaram na versão final. 114 frontend, TypeScript e build passaram.
Sem commit/push. Serviços atuais: API 8000 sessão 95485, Vite 5173 sessão 84637.

Verificação mais recente: 383 testes API e 106 frontend passaram; build e Ruff passaram. Presenças: ADR-064.

## Presenças por refeição — incremento de 18 de outubro de 2026

O percurso guiado permite exceções por data/refeição ao grupo habitual e guarda-as no
JSON versionado da semana. Slots enviam os presentes ao motor; as exclusões automáticas,
porções e limites nutricionais usam só esses participantes. Refeições sem presentes não
são geradas. O backend rejeita participantes fora do grupo e sobreposições da mesma pessoa.

T04 permanece parcial: padrões reutilizáveis, incerteza e refeições individuais no percurso
ficam pendentes; para uma pessoa o ecrã indica a agenda e bloqueia geração incorreta.
Não houve migration nem gravação de refeições pessoais nesta verificação de interface.

# Domain implementation status

Current local increment (2026-10-18, ADR-063): complete versioned Family recipe variants
with immutable effective Recipe projections, full composition, participant validation,
activation/retirement, source/label invalidation, weekly selection and effective shopping.
Schema head `58960d47819f`. Full regression: 378 API / 102 web tests passed, build passed.
Initial context is a selected group/date/meal; per-slot attendance and product-pack mapping
remain pending. No real Family variant was activated in this verification.

Final verification supersedes the intermediate count above: 379 API / 104 web tests,
TypeScript/build passed; browser workflow reached applied weekly meals and substituted
shopping on an isolated synthetic Family. See the current execution task board.

Latest steering (2026-10-18): automatic restriction preselection from effective structured
diet rules and a configured active SIBO/FODMAP planning profile; automatic rules are
rechecked per weekly slot on preview/accept. Source/reason/date and base ingredient
alternatives are visible. See ADR-062. Complete multi-operation variants remain pending;
base recipe cards are explicitly review proposals, not applied substitutions.

Latest local increment (2026-10-18, not merged): guided next-week planning through shopping,
versioned Family week choices, additional explicit ingredient exclusions checked during
proposal and acceptance, four sourced retail candidates, and verified snapshot batch basis
for legacy shopping. Schema head `d7c626668227`; 359 API / 97 web tests passed.
See `guided-week-planning-and-retail-alternatives.md`, ADR-061. Shared generation still
uses one common group of at least two people; retail suggestions do not modify recipes.

Next planned integration (2026-10-18, not implemented): per-meal attendance and groups,
complete Family variants selected by present participants' explicit rules, and unified
recipe/delivery/restaurant discovery plus map. See the current next-work plan in
`docs/vision/integrated-family-meal-planning-roadmap.md` and ADR-060.

## Latest local branch increment — 2026-10-18

On `codex/health-conditions-fodmap-review` (not merged): Person health conditions with revision
history, per-Family recipe substitution review, public educational FODMAP reference selection
and UI under Person Health / Home Substitutions. Schema head `3ecd05b9b43a`.
No automatic diet is inferred from a condition and no source recipe is changed by the review.
See `health-conditions-and-fodmap-review.md`; schema labels in older sections below describe
their original feature checkpoints.

`docs/development-continuity.md` is the handover entry point. This file summarizes the current domain baseline and the next planned capability.

## Current Nutrition Plan chain

```text
NutritionPlan domain/provenance                    IMPLEMENTED
EffectiveNutritionPlan compiler                   FOUNDATION IMPLEMENTED
Plan text/document import + review/confirmation   IMPLEMENTED v1
AI-assisted text interpretation + review UI       IMPLEMENTED v1
MealPlanFit candidate evaluation                  IMPLEMENTED v1
Structured Meal Transformation                    IMPLEMENTED v1
Plan-Fit-aware recommendation integration         IMPLEMENTED v1
Shared-Family transformation + materialization    IMPLEMENTED v1
Adaptive weekly planning                          IMPLEMENTED v1
Weekly plan -> shopping coupling                   IN PROGRESS
```

Feature schema head for Structured Meal Transformation:

```text
d2e6f1a9c4b7
```

It adds Family-scoped `FoodTransformationProfile` metadata. Meal transformation proposals themselves remain calculation-only.

## Person, Family and health context

Implemented:

- Family and Person;
- editable Person profile and energy inputs;
- anthropometric history;
- NutritionGoal history;
- versioned NutritionTarget components;
- NutritionConstraint with provenance/severity/mandatory semantics;
- FoodPreference and adverse-reaction evidence;
- ScheduleEntry context;
- HealthConnection / HealthMeasurement foundations;
- DailyHealthState and DailyNutritionState snapshots.

## Nutrition Plan / Guidance

Implemented:

- versioned Person-scoped NutritionPlan lineage and lifecycle;
- source/provenance and original source text/reference;
- draft-only editing and immutable active plan content;
- NutritionPlanRule bindings to constraints, target components and goals;
- meal scope, priority, date validity and source statement;
- NutritionPlanGuideline for qualitative/frequency guidance;
- deterministic EffectiveNutritionPlan compilation for Person/date/meal type;
- source/mandatory ordering without silent rule deletion;
- numeric conflict reporting;
- reviewed text import through NutritionPlanImportSession/Proposal;
- conservative PT/EN deterministic parser v1;
- optional AI-assisted interpretation using structured output;
- explicit proposed/confirmed/rejected review gate for deterministic and AI interpretation;
- `unclassified` ambiguity preservation;
- browser import/review surface under Person Nutrition;
- confirmed proposal materialization into draft plan content;
- separate explicit activation after import apply.

Deferred plan ingestion:

- PDF/photo/document extraction into the existing text-review boundary.

## Meal Plan-Fit v1

Implemented in PR #39:

- one server-authoritative evaluator for FoodItem and Recipe candidates;
- versioned composition scaling and safe unit conversion;
- EffectiveNutritionPlan as the rule source;
- meal-scoped numeric guidance compared directly with candidate evidence;
- candidate-level exclusions from normalized subjects;
- global nutrient guidance treated as daily context rather than a per-meal target;
- DailyNutritionState supplied explicitly or auto-selected for Person/date;
- projected daily totals include existing state plus candidate contribution;
- daily minimum/range rules can return `support`;
- mandatory machine-evaluable nutrient rules with missing context/evidence fail closed as `unknown`;
- mandatory guidance outside the current meal-evaluable scope (for example lifestyle, supplement, timing or unsupported qualitative directives) remains visible as partial coverage instead of becoming a universal meal veto;
- mandatory weekly maxima still fail closed when safe remaining capacity cannot be established from structured evidence; weekly minima remain support signals rather than per-meal gates;
- mandatory adverse reactions remain independent hard gates;
- mandatory plan conflicts block eligibility;
- overall status is independent from numeric score;
- fit score is 0..1 over scored candidate/meal numeric rules only;
- qualitative/frequency guidance remains visible as `not_evaluated`;
- provenance is preserved in each result;
- weekly proposal participants expose the exact derived NutritionPlan authority used by their Person-specific Plan-Fit, instead of reducing the result to `status=unknown`/score only;
- imported explicit prohibitions can be materialized as structured `exclude` constraints without numeric values; unsupported category evidence remains partial rather than inferred from names;
- no provider-specific scoring semantics.

API:

```text
POST /api/persons/{person_id}/meal-plan-fit
```

Web surface:

```text
Pessoas -> <Person> -> Nutrição -> Adequação ao plano
```

## Structured Meal Transformation v1

Implemented in Phase 5 proposal slice:

- Family-scoped `FoodTransformationProfile` with explicit `substitution_group`;
- optional typical portion quantity/unit for explicit substitution equivalence;
- source/source-reference provenance and an enable flag;
- deterministic single-ingredient `replace_ingredient` operation;
- source Recipe remains immutable;
- baseline and transformed candidates use the same Meal Plan-Fit evaluator semantics;
- transformed nutrition is calculated virtually from composition evidence;
- unsafe conversions and incomplete evidence are skipped and exposed as limitations;
- only demonstrably improving replacements are returned;
- resolving a mandatory eligibility block is ranked above score-only improvement;
- daily-rule progress can qualify as an improvement without misreading daily targets as meal targets;
- proposal response contains before/after Plan-Fit, score delta, changed rule IDs and hard-block resolution;
- compact browser control appears only after evaluating a Recipe and exposes `Sugerir melhoria`.

API:

```text
POST /api/persons/{person_id}/meal-transformations/proposals
```

Development example:

```text
Iogurte, muesli e banana
baseline ~= 96.67%, blocked by breakfast protein >= 15 g

Iogurte natural 170 g -> Iogurte grego 170 g
result = 100%, eligible
```

The yogurt composition evidence used for this example is explicitly synthetic development data.

Decision/domain docs:

- `docs/decisions/ADR-039-structured-meal-transformation-proposals.md`
- `docs/domain/meal-transformation.md`

Deferred transformation work:

- persistent reusable Recipe-variant authoring after explicit acceptance;
- multiple simultaneous ingredient operations;
- add/remove/increase/reduce and cooking-method operations;
- pantry/cost/preparation optimization;
- AI/learned substitution generation without structured evidence.

## Catalogue and recipe evidence

Implemented:

- Family/shared FoodItem catalogue;
- versioned FoodCompositionSnapshot and nutrients;
- Recipe / RecipeIngredient;
- deterministic recipe composition calculation;
- versioned RecipeCompositionSnapshot;
- explicit nutrition provenance/readiness;
- safe conversions only; missing evidence remains unknown.

## Meals and household operations

Implemented:

- MealEvent + MealParticipant + Person-specific Serving;
- fixed meal types breakfast/lunch/snack/dinner;
- Today/Week family planner;
- planned-meal replacement/idempotency;
- immutable historical serving nutrition evidence;
- deterministic DailyNutritionState recalculation;
- pantry stock and expiry;
- aggregate planned ingredient requirements;
- durable shopping lists/items.

## Recommendation foundation

Implemented:

- hard-rule-first recommendation ranking;
- fail-closed mandatory evidence handling;
- legacy nutrition-fit score;
- preferences and Family aggregate preference;
- practical schedule/location/preparation context;
- shared-family recommendation with per-Person safety;
- persisted runs/options/feedback/decisions;
- diversity/history/repeat penalties;
- meal suitability and calorie-aware refinements.

Next integration rule: recommendation ranking must consume MealPlanFit for nutrition-plan-aware eligibility/fit instead of allowing its legacy nutrition-rule evaluation to evolve independently. Preference, practical context and diversity remain separate ranking layers.

## Adaptive weekly planning v1

Implemented:

- deterministic Person-specific weekly frequency progress;
- weekly-aware Meal Plan-Fit support/minimum and mandatory-maximum semantics;
- Person-specific weekly support in shared-Family ranking;
- full-week multi-slot optimization with same-day mandatory nutrient coupling;
- shared-Family weekly optimization using each Person's own Meal Plan-Fit evidence;
- server-authoritative weekly proposal orchestration;
- deterministic bounded search for larger candidate spaces;
- safe transformed Recipe variants participating directly in weekly optimization;
- atomic weekly materialization with stale-selection and slot-conflict protection;
- Monday-Sunday Week view with progressive disclosure and local rejection/recalculation;
- persisted transformation provenance visible after the weekly plan is applied;
- server-authoritative unavailable slots remain explicit pending gaps instead of invalidating the rest of an otherwise feasible week;
- exact recipe repetition inside one proposed week carries a soft plan-level diversity penalty, including in bounded-search pruning, without weakening Plan-Fit or mandatory weekly rules.

Current coupling increment:

- after successful weekly materialization, refresh the existing pantry-aware durable shopping list for the same Monday-Sunday interval;
- calculate transformed meals from persisted replacement ingredient provenance rather than the source Recipe ingredient;
- keep shopping refresh derivative: failure is surfaced separately and does not make an already-saved week appear rolled back.

## Restaurant and delivery foundation

Implemented abstractions:

- `MealCandidateAvailability` for home, pantry, restaurant, delivery and store;
- opening windows;
- commercial offers with provider/price/fees/minimum order/validity;
- external-menu normalization into FoodItem + optional composition + availability/offer.

Future restaurant/delivery Plan-Fit must use the same normalized evaluator. Provider access/configuration remains outside nutrition scoring.

## Safety and correctness invariants

Preserve:

- adverse reactions and mandatory constraints before ranking/ML;
- active professional-plan immutability;
- explicit parser review before imported content becomes plan content;
- separate explicit activation after import;
- missing evidence is unknown, not zero;
- unsafe conversion is rejected;
- mandatory missing evidence/context fails closed when needed;
- high fit score cannot override a hard failure or conflict;
- daily targets are not naively treated as per-meal targets;
- transformation proposals never silently mutate source Recipes;
- transformation equivalence requires explicit metadata/evidence rather than name inference;
- professional provenance is retained;
- conflicts are surfaced;
- Family isolation and Person-specific portions;
- historical Serving evidence remains stable;
- demo evidence is explicitly synthetic/development-only;
- warnings are failures.

## Next development block

Current branch: weekly plan -> shopping-list coupling.

After this slice is reviewed and eventually merged, the next Phase 8 work should remain focused on one product-visible capability at a time. Candidate increments are richer across-week category/protein diversity, explicit leftover/reservation evidence, or deeper pantry/schedule coupling. Do not start the next branch until this slice has been reviewed and merged explicitly.

## Broader deferred limitations

- production authentication / Family authorization;
- shopping purchase -> pantry reconciliation;
- trustworthy catalogue coverage is incomplete;
- production consumer marketplace adapters depend on provider access;
- OCR/photo/scanned-document extraction;
- qualitative guidance remains only partially machine-evaluable;
- transformation reusable-variant authoring and multi-operation optimization;
- explicit leftover/reservation inventory evidence;
- richer across-week category/protein diversity;
- npm lockfile / `npm ci` production hardening.
