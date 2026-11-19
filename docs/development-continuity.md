> **Estado atual — 19 novembro 2026:** consultar [passagem e próximos passos](handoff-2026-11-19.md) e o [quadro UX](vision/ux-revamp-task-board.md). Os estados de branches, contagens e “próxima tarefa” abaixo são históricos. Esta entrega consolida o revamp, o fluxo de trocas e o lote de 20; NLP/ML treinado e restantes fases continuam na sequência canónica.

## Preview do novo UX — 18 novembro 2026

Branch local `codex/ux-foundation-preview`, empilhada em `e34d9e0` por autorização do utilizador para iniciar o revamp e testar localmente. PRs anteriores permanecem sem merge. Preservar os ficheiros egg-info já modificados, package-lock não rastreado e os documentos de auditoria.

Primeira fatia: tokens semânticos com aliases para ecrãs existentes; claro marfim/verde, escuro carvão/âmbar; marca NutriFlow AI / Casa à Mesa; ícones SVG; home compacta com dados reais; avatares estáveis e microinterações sem loops, com movimento reduzido; seletor direto de tema/idioma no cabeçalho. Perfis, planeamento, variantes e compras existentes preservados; rotas/URLs, restantes ecrãs e presença no avatar continuam por migrar.

PostgreSQL principal acessível, Alembic head observado `b781e265c904`. Uma DB separada `nutriflow_ux_validation_20261118` foi criada para migrations/Alembic check e 438 testes API, todos passaram. 153 testes frontend e TypeScript/build passaram. Sem migrations novas, seeds ou alterações na família principal. Sem captura de ecrã ou nova afirmação de validação visual completa.

Servidores locais arrancados em 127.0.0.1:8000 (API) e 127.0.0.1:5173 (Vite), processos/logs de preview em `.cache/ux-preview.json` e `.cache/ux-*.log`. Verificar portas/processos antes de iniciar duplicados. Esta preview usa a configuração local da API, não a base de testes. Os logs são ignorados pelo Git.

Estado e próximos passos: `docs/vision/ux-revamp-task-board.md`, `docs/ux/nutriflow-design-direction.md` e `docs/ux/auditoria-ux-2026-11-18.md`. Próximo: feedback da home/temas, normalização dos controlos e detalhe da refeição/agenda; não migrar o motor demonstrativo do HTML. Fazer revisão visual em dados sintéticos e terminar a sessão de captura explicitamente se for usada.

## Receções parciais e validade por refeição — ADR-072 (18/10/2026)

Compras recebem vários lotes com local/validade próprios e entregas parciais versionadas.
Stock útil, previsão por receber e quantidade por comprar são separados. Fechar sem mais
produtos recalcula a falta imediatamente; pedidos repetidos não recriam lotes/histórico.
Correção da validade: orçamento FEFO por data/hora das refeições, sem consumir inventário.
Sessão real `autoflush=False` coberta por testes; flush explícito antes do recálculo evita
perder o novo snapshot. Entradas antigas continuam concluídas e compatíveis.
Sem migration: head b781e265c904 e 53 tabelas aplicacionais. Família real sem entradas
criadas pelo agente; verificação no browser numa base sintética separada.
438 testes API completos, 17 focados de produção e 147 frontend passaram; build, Ruff e
Alembic check sem erros. Interface verificada com persistência e fecho de entrega incompleta.

## Comparação de lojas no ingrediente — ADR-071 (18/10/2026)

Comparação por €/kg ou €/l, com preço por embalagem, fonte/data e cobertura do rótulo.
Grupos comerciais e dimensões físicas separados; nenhum produto vira equivalente clínico
ou substituição aplicada por aparecer com menor preço. Descoberta mantém outras lojas
para ingredientes confirmados, sem relaxar a identidade exigida para comprar o produto.
Só um detalhe de rótulo aberto de cada vez. Onze observações existentes; sem consulta live
neste incremento. Sem migration; head b781e265c904 e 53 tabelas aplicacionais preservados.
421 testes API completos, 36 focados e 140 frontend passaram; build, Ruff e Alembic check sem erros.
Browser verificado numa família sintética, sem alterar a família real.

## Entrada das compras na despensa — ADR-070 (18/10/2026)

Cartão comprado permite confirmar quantidade real/unidade/local/validade e criar um lote.
Versão, revisão explícita e unidade compatível obrigatórias; rótulos alterados bloqueiam.
Snapshot histórico e chave única evitam duplicação por retry, mesmo após desativar o lote.
Compras recebidas não são apagadas/desmarcadas; regenerar permite uma nova compra futura.
Migration b781e265c904 aplicada após backup privado; família real sem entradas criadas.
Interface verificada numa base sintética: 1.500 g recebidos mais 100 g existentes → falta zero.
407 testes API e 132 frontend passaram; build, Ruff e Alembic check sem erros.
Mais detalhes e limites em ADR-070; comparação entre lojas e receções parciais pendentes.

## Produtos confirmados e embalagens — ADR-069 (18/10/2026)

Implementado ingrediente próprio a partir de rótulo revisto, ligação exata às compras,
pré-visualização e escolha versionada de embalagens. Quantidades são as efetivas depois
do stock; propostas do original não servem como identidade do substituto. Mudanças
invalidam nova utilização e exigem revisão; compras históricas mantêm snapshot.
Migration 93c8e18311c4 em teste/live, com backup e ciclo reversível na base isolada.
20 testes API focados, 128 frontend e build passaram; regressão completa 399 passou
antes dos ajustes finais de catálogo/rollback. Interface em base sintética própria.

## Continuação: organização reutilizável e agenda segura — ADR-068

Copiar semana anterior e repetir um grupo por tempo implementados no percurso. As regras
são recalculadas e a configuração só persiste após revisão. Agenda manual de receitas-base
passa a rejeitar ingredientes excluídos para os presentes/data, com rollback integral.
Sem migration; sem alteração de refeições pessoais nesta implementação. Testes focados
390 API completos e 123 frontend passaram; interface verificada sem guardar alterações.
Caso adicional de grupo grande coberto pela execução focada final. Ruff e Alembic check passaram.

## Auditoria e retalho após publicação — 18/10/2026

Branch publicada, consolidação `5aab9e3`, sem merge. Onze observações de retalho
após sete novas; importação idempotente, sem alteração de receitas/quantidades.
Backup local anterior à importação preservado. Auditoria pública sanitizada em
`docs/domain/technical-audit-2026-10-18.md`, inventário do esquema e fontes de retalho
nos documentos da mesma data. 119 testes frontend e 14 testes workspace passaram;
build final passou após lazy loading das compras. Regressão final completa: 388 testes API passaram.
O histórico abaixo contém estados intermédios; o quadro de tarefas é a referência atual.

## Publicação e revisão — 18/10/2026

Consolidação T01–T06/T08 preparada na branch v2 por autorização explícita.
118 testes web e build passaram; Ruff e Alembic check passaram. Auditoria do esquema
inventaria 52 tabelas de aplicação e a tabela Alembic; sem exportar linhas pessoais.
Backups, capturas e relatórios pessoais em docs/audits ficam locais e ignorados pelo Git.
O quadro de tarefas distingue execução atual de registos históricos abaixo.

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

# NutriFlow AI v2 development continuity

## Complete recipe variants — current increment (2026-10-18)

Final verification: 379 API tests, 104 web tests and final build passed. Browser test
completed draft → validation → activation → weekly application → effective shopping on
the isolated DB. UI regressions fixed: active variants missing from base summaries,
false error on already-planned slots, unnecessary decimal zeros. See
`docs/audits/2026-10-18/complete-variant-interface-verification.md`. T02/T03 are locally
verified; T04 attendance is next, T05/T06 remain partial. No real Family variant was created.

Schema head `58960d47819f`, parent `d7c626668227`. FamilyRecipeVariant now stores
immutable complete ingredient projections through ordinary Family Recipe/Composition
entities, with lineage/revision, concurrency version, operation evidence and fingerprints.
Draft → validation for selected people/date/meal → activation is exposed inside the
existing substitution review. Base recipes remain unchanged; generic mutation is blocked.
Active fresh variants enter normal recommendation/weekly planning and effective shopping.
Proposal and saved grid show operation summaries. Server validation/acceptance checks all
participants; changed source/label evidence blocks new use. Retired variants preserve history.

378 full API tests, 102 frontend tests and production build passed before final interface
verification. Isolated migration upgrade/downgrade/upgrade and live Alembic check passed.
Live migration followed `backups/pre-complete-variants-2026-10-18.dump`. No real Family
variant or meal was activated/applied by the agent. ADR-063 records design and limitations.

UI integration uses a second API on 8001 and Vite on 5174 targeting
`nutriflow_review_test`, with `python -m tests.seed_variant_ui` (database-name guarded).
Default app remains 8000/5173. Never seed that synthetic fixture into the live database.
Per-slot attendance, richer product linking/pack selection and external discovery remain
pending; complete variants do not imply those capabilities are finished.

Execution task board: `docs/vision/implementation-task-board.md`. The current next slice
is editing existing substitution quantities/units/preparation notes; complete variants,
attendance, automatic variant selection and substituted shopping remain tracked there.

T01 completed locally: existing substitution PUT can update/clear quantity+unit together
while omitted fields are preserved. Review UI edits whole-recipe replacement quantity,
unit and notes. Version conflicts and invalid pairs are rejected; base recipes unchanged.
21 dietary-review API tests, 99 web tests, TypeScript and production build passed.
No migration. Next: complete pilot variant (T02) and all-participant validation (T03).

## Latest steering — automatic defaults and visible substitutions (2026-10-18)

ADR-062 supersedes manual-only defaults from ADR-061. Added scoped POST
`/api/families/{family_id}/planning-restrictions`: selected participants/date/meal-aware
effective plan exclusions and the explicitly requested `sibo` → FODMAP planning profile.
Weekly preview/accept recompute automatic exclusions per slot. UI preselects and explains
the source; manual week selections are stored separately. No migration was needed.
Base recipe cards expose all affected ingredients, alternatives, review state and missing
quantities; existing executable transformations now display the actual swap in the grid.
Validation: 98 web tests and final production build passed; 23 weekly/workspace API
integration tests passed after a cache-ordering regression found in the full run was
fixed. See ADR-062 for the exact validation scope.

Verified locally: the affected participant activates the profile for 19–25 October; 57 catalogue recipes
have mapped affected ingredients, with visible pending changes. These are review drafts,
not complete executable variants. Unchanged incompatible bases remain blocked by the
weekly engine. Full multi-operation validation/materialization/shopping is still pending.

## Latest local increment — guided week and shopping (2026-10-18)

Implemented locally on `codex/health-conditions-fodmap-review`: Home → Plan next week →
people/meal types → explicit ingredient exclusions → review/apply → shopping. Versioned
Family week setup, exclusion checks on preview and accept, four sourced supermarket
observations, shopping suggestions and verified snapshot serving-basis fallback.
Schema head `d7c626668227` is applied locally. Public educational references total 23;
no licensed FODMAP database was extracted. Validation: 359 API tests, 97 web tests,
TypeScript and production build passed. See
`docs/domain/guided-week-planning-and-retail-alternatives.md` and ADR-061.

The shared wizard uses one group (at least two people) for its generated meals. Per-slot
attendance, complete multi-operation variants and live delivery integrations remain
unfinished. The roadmap below remains the target; the older “no implementation” statement
describes that earlier planning-only checkpoint, not this new increment.

## Next product sequence — integrated Family planning (2026-10-18)

Authoritative next-work plan: `docs/vision/integrated-family-meal-planning-roadmap.md`, ADR-060.
Resolve participants per meal/group using weekly patterns and date exceptions, then explicit
restrictions, complete Family variants and shared source discovery. A global weekly `person_ids`
list is insufficient. Reuse individual/shared evaluators; do not infer diets from conditions.

First functional increment: attendance + usable restrictions + one verified complete recipe
variant through daily/weekly planning. Then catalogue coverage, unified source panel/map and
authorized live adapters. The 130 current alternatives remain review proposals.

Current local provider diagnosis: no credentials, consumer enablement or registered live adapter
for Uber Eats/Glovo/Bolt Food; Google Places key absent; OSM discovery implemented. Family area
and delivery defaults exist. No external network smoke test was run in this planning review.
Official Uber consumer access is approval-controlled; Glovo Partner docs do not prove consumer
marketplace access. Adding keys alone does not implement adapters.

This sequence supersedes older next-branch suggestions below. No implementation, provider
activation, recipe application or database mutation was performed for this planning update.

## Latest local increment — health conditions and FODMAP substitution review (2026-10-18)

Current branch: `codex/health-conditions-fodmap-review`, based on weekly comparison head
`9823b4d716e34b0829b6b57ff3732c46d5bc156c`. This is stacked review work, not an integration
of the pending weekly branches. New schema head: `3ecd05b9b43a` (parent `e3f7a2b6c1d9`).

Implemented Person health-condition create/revise/history, immutable condition event snapshots,
Family-scoped recipe substitution review and a documented 22-item public Monash guidance import.
UI: `Pessoas → pessoa → Saúde` and `Casa → Substituições`. Local Family data has 130 review
proposals; source recipes and historical Servings were not changed. A requested user-reported
condition was registered separately through the service without baking patient data into code.

Validation: isolated-database migration downgrade/upgrade, Alembic check, Ruff, 349 API tests,
92 web tests, TypeScript/build and browser read-only smoke checks passed. See
`docs/domain/health-conditions-and-fodmap-review.md` and ADR-059 for source limitations and
the next stage. No diagnosis-to-diet automation, licensed laboratory database import or actual
recipe application was introduced. Existing pending PRs were not merged.

The remaining sections preserve prior checkpoints; branch/schema labels below are historical.

This is the authoritative handover entry point for NutriFlow AI v2. Repository code, migrations, tests, domain docs and ADRs take precedence over conversation history.

## Repository checkpoint

Nutrition Plan / Guidance capability blocks:

```text
PR #37  NutritionPlan + EffectiveNutritionPlan foundation                  MERGED
PR #38  reviewed text import / confirmation boundary                       MERGED
PR #39  deterministic Meal Plan-Fit evaluation + focused test UI           MERGED
PR #42  AI-assisted text interpretation + browser review UI                MERGED
PR #43  Structured Meal Transformation proposals                           MERGED
PR #44  PDF/DOCX/TXT/Markdown text extraction into import review           MERGED
PR #45  scoped single-Person recommendations consume Meal Plan-Fit          MERGED
PR #46  shared-family recommendations use Person-specific Meal Plan-Fit     MERGED
PR #47  restaurant/delivery recommendations consume Meal Plan-Fit           MERGED
PR #48  deterministic weekly frequency progress                            MERGED
PR #49  individual recommendations use weekly frequency progress           MERGED
PR #50  Person-specific weekly support in shared-family ranking             MERGED
PR #51  full-week multi-slot planning foundation                            MERGED
PR #52  same-day daily nutrient coupling                                    MERGED
PR #53  shared-Family multi-slot planning                                   MERGED
PR #54  server-authoritative weekly planning proposal API                   MERGED
PR #55  bounded/scalable weekly search                                      MERGED
PR #59  NutritionPlan authority across Plan-Fit                             MERGED
PR #60  shared-Family recipe transformation evaluation                      MERGED
PR #61  NutritionPlan authority UI                                          MERGED
PR #62  recommendation authority UI                                         MERGED
PR #63  Family transformation preview in recommendations                    MERGED
PR #64  materialized shared recipe transformations                          MERGED
PR #66  weekly planning selects safe recipe adaptations                     MERGED
PR #67  atomic weekly plan materialization                                  MERGED
PR #68  current Week-view frontend                                          MERGED
PR #69  persisted transformed meals in Family planning                      MERGED
current weekly plan -> shopping-list refresh + transformed shopping         IN PROGRESS
```

Confirmed `main` before the current branch:

```text
2d93327a169d691fe4dd5f566da94603ac09a406
```

Current focused branch, created from that exact main SHA:

```text
feature/week-shopping-list-refresh
```

The current slice adds no migration. Repository schema head remains:

```text
d2e6f1a9c4b7
```

Do not treat any SHA in this file as permanently current. At every new session resolve `refs/heads/main`, inspect the open PR and confirm CI on the exact final head before merging or starting new work.

The API test environment currently caps development/test AnyIO below 4.15 because Starlette 1.6.0 TestClient still imports a deprecated AnyIO alias and this repository treats warnings as errors.

## Product direction

NutriFlow AI v2 is a Person-centric adaptive nutrition platform inside Family context. Professional guidance is compiled once into authoritative planning evidence and reused by meal evaluation, recommendations and week-level planning.

Current operational chain:

```text
Person / Family
-> goals, targets, constraints
-> versioned NutritionPlan
-> EffectiveNutritionPlan per date + meal
-> reviewed text/document import
-> FoodItem / Recipe composition + explicit planning metadata
-> MealPlanFit for candidate + exact Person-specific portion
-> Person-specific weekly frequency progress
-> weekly-aware MealPlanFit guideline evidence
-> Structured Meal Transformation proposals
-> single-Person / shared-Family / external recommendation paths
-> practical availability + preference + diversity + feedback
-> adaptive candidate ordering from weekly support
-> multi-slot weekly composition over existing Meal Plan-Fit evidence
-> same-day recomposition of mandatory daily nutrient upper bounds
-> shared-Family multi-slot composition by reusing each Person's weekly projection
-> server-authoritative weekly proposal API
-> explicit weekly acceptance/materialization boundary
-> Family MealEvent + Person-specific Servings
```

Authoritative product roadmap: `docs/vision/nutrition-plan-guidance-roadmap.md`.

Key ADRs:

- ADR-035 Nutrition Plan guidance foundation
- ADR-036 Nutrition Plan import/review boundary
- ADR-037 Meal Plan-Fit evaluation
- ADR-038 AI-assisted Nutrition Plan import
- ADR-039 Structured Meal Transformation proposals
- ADR-040 document extraction feeds the review boundary
- ADR-041 scoped recommendations consume Meal Plan-Fit
- ADR-042 shared-family recommendations use Person-specific Meal Plan-Fit
- ADR-043 external commercial recommendations use normalized persisted evidence and Meal Plan-Fit
- ADR-044 weekly frequency progress uses structured meal evidence
- ADR-045 weekly frequency guidance extends Meal Plan-Fit
- ADR-046 shared-family weekly support remains Person-specific
- ADR-047 full-week planning consumes Meal Plan-Fit evidence
- ADR-048 weekly planning rechecks daily nutrient limits across same-day slots
- ADR-049 shared-family weekly planning reuses Person-specific weekly planning
- ADR-050 weekly planning API is server-authoritative

## Core invariants

Preserve these rules:

- Person is the primary nutrition entity inside Family context.
- One shared MealEvent can have multiple MealParticipants and Person-specific Servings.
- Normal meal types are exactly `breakfast`, `lunch`, `snack`, `dinner`.
- Nutrition Plan is distinct from Meal Plan.
- Active professional-plan content is immutable; substantive changes create a new version.
- Source/provenance and original statements remain traceable.
- Parser/AI interpretations never silently become active professional rules.
- Missing nutrition or classification evidence is unknown, never silently zero.
- Unsafe unit conversions are rejected rather than guessed.
- Mandatory adverse reactions and mandatory nutrition rules are hard gates before preferences/ranking/ML.
- A numeric fit score never overrides a mandatory failure, conflict or safety block.
- Daily guidance must not be naively interpreted as a per-meal target.
- Weekly minimum frequency guidance must not be naively interpreted as a per-meal mandatory target.
- Mandatory weekly maxima fail closed when remaining safe capacity cannot be established from available structured evidence.
- User preference remains separate from nutrition/practical fit.
- Professional guidance is not silently overridden by lower-authority guidance.
- Conflicts are surfaced, not silently resolved.
- Historical Servings and composition provenance remain stable when catalogue data changes.
- Structured transformations never silently mutate their source Recipe.
- Practical availability, price, family preference, diversity and feedback may rank an eligible meal but may not reverse Meal Plan-Fit ineligibility.
- Shared-family Plan-Fit is Person-specific; one Person's plan or weekly evidence must never be copied to another Person.
- Any hard failure for any shared-meal participant excludes that shared candidate before Family-level ranking.
- External items without persisted composition evidence are not nutrition-ranked.
- Weekly frequency evaluation never classifies food from names/descriptions; only persisted structured planning evidence may count.
- Recommendation and week-planning code consume weekly evidence from Meal Plan-Fit rather than implementing another frequency evaluator.
- Weekly minimum support is ranking/optimization pressure only; it is never an obligation for one meal slot.
- Full-week planning must recheck constraints that can be violated only by the combination of several individually eligible choices.
- Same-day daily nutrient coupling consumes structured Meal Plan-Fit rule evidence; it does not reload/reinterpret NutritionPlan rules or silently convert units.
- Shared-Family multi-slot planning must project the shared choice through every Person's exact participant evaluation and Plan-Fit before Family aggregation.
- Support for one Person can never rescue a weekly or daily hard failure for another Person.
- Weekly planning clients submit ordinary planning inputs; Plan-Fit and recommendation evidence remain server-authoritative.
- Proposal generation must not silently create MealEvents; weekly acceptance is an explicit later action.
- Browser code presents server-authoritative nutrition/planning evidence.
- Persisted timezones are valid IANA names.

## Recommendation integration

Single-Person, shared-Family and external restaurant/delivery production recommendation paths consume common Meal Plan-Fit semantics when an explicit meal scope exists.

External restaurant/delivery observations are normalized to ordinary catalogue abstractions:

```text
FoodItem
+ optional versioned FoodCompositionSnapshot
+ MealCandidateAvailability
+ MealCommercialOffer
```

Commercial items without nutrition composition remain visible but unranked. Price/provider/preference cannot override mandatory Plan-Fit failure.

## Phase 8a — weekly frequency progress — DONE v1

PR #48 added the deterministic server-authoritative read model:

```text
GET /api/persons/{person_id}/weekly-frequency-progress?on_date=YYYY-MM-DD
```

It resolves Monday-Sunday in the Person's IANA timezone, consumes confirmed weekly frequency guidance from EffectiveNutritionPlan, counts Person-specific MealParticipant/Serving evidence, separates completed/planned occurrences, reports provenance and remaining minimum/capacity, and marks lower-bound counts when structured classification is incomplete.

Supported structured targets in v1:

```text
food_category
food_group
planning_category
primary_protein
food_item
recipe
```

`food_category`/`food_group` resolve only through explicit `MealCandidatePlanningProfile` metadata. Names and descriptions are never classification evidence. Unsupported targets remain `unknown` with numeric fields `null`.

## Phase 8b — individual weekly-aware candidate selection — DONE v1

PR #49 extended production Meal Plan-Fit with Phase 8a weekly evidence instead of introducing a separate nutrition evaluator.

A candidate matching a confirmed remaining weekly minimum receives `support`. A non-matching candidate is not blocked because later meals can still satisfy the minimum. Mandatory weekly maxima fail or fail closed when structured evidence cannot prove safe capacity. Weekly support remains separate from numeric `fit_score`.

Among already eligible individual candidates, ranking orders confirmed mandatory-minimum support first, then advisory-minimum support, then preserves the previous recommendation ranking.

## Phase 8b extension — shared-Family weekly adaptation — DONE v1

PR #50 keeps every participant's weekly evidence independent:

```text
Person A portion -> Person A Meal Plan-Fit -> Person A guideline_results
Person B portion -> Person B Meal Plan-Fit -> Person B guideline_results
...
-> exclude candidate if ANY Person fails a hard gate
-> aggregate only weekly support evidence for the remaining eligible candidate
-> Family ordering
```

Shared ordering is deterministic:

```text
mandatory-support participant coverage
-> total mandatory support statements
-> advisory-support participant coverage
-> total advisory support statements
-> minimum participant score (fairness)
-> average score
-> candidate key
```

The common weekly recommendation adapter owns interpretation of `guideline_results` into mandatory/advisory support counts. The shared layer only aggregates Person-specific results. Diversity and feedback score adjustments reapply the canonical shared ranking so they cannot erase higher weekly support.

ADR: `docs/decisions/ADR-046-shared-family-weekly-support-is-person-specific.md`.

## Phase 8c — full-week multi-slot optimization — IN PROGRESS

PR #51 merged the deterministic one-Person/one-week foundation. PR #52 extended it with same-day recomposition of mandatory nutrient upper bounds. PR #53 added shared-Family multi-slot planning while reusing every Person's existing weekly optimizer.

Person-level input boundary:

```text
slot
-> CandidateEvaluation
-> MealPlanFitRead
-> structured rule/guideline evidence
```

The merged Person planner:

- accepts only candidates already eligible in recommendation and Meal Plan-Fit;
- preserves structured weekly classification evidence and lower-bound uncertainty;
- rechecks mandatory weekly maxima over the whole selected combination;
- rewards confirmed mandatory weekly minimum deficits before advisory deficits;
- caps minimum-support credit at confirmed remaining deficit;
- recomposes mandatory same-day nutrient upper bounds against the common DailyNutritionState baseline;
- keeps daily coupling isolated per date;
- compares minimum candidate score, average score, exact-repeat count and stable candidate keys;
- refuses search spaces above an explicit deterministic combination limit.

The merged shared-Family planner keeps one participant evaluation and one Meal Plan-Fit per Person. For each proposed shared combination it projects the selected shared meals into one singleton-candidate weekly plan per Person and calls the existing Person optimizer. The shared combination is feasible only when every Person projection is feasible.

Family ordering among feasible combinations is:

```text
mandatory-support participant coverage
-> total mandatory supported occurrences
-> advisory-support participant coverage
-> total advisory supported occurrences
-> diversity-adjusted minimum participant score
-> diversity-adjusted average participant score
-> repeated shared-candidate count
-> stable candidate-key sequence
```

Exact recipe repetition inside the proposed week is a soft diversity cost, not a hard gate. Each occurrence beyond the first subtracts 0.25 from the plan-level minimum and average ranking scores. Mandatory/advisory weekly support remains ahead of that adjustment, and clearly worse alternatives can still lose to a repeated favourite. The bounded search applies the same repeat-aware score hint before pruning so approximate search does not systematically collapse onto the same top-ranked recipe.

Current increment: couple an explicitly applied weekly plan to the existing durable shopping-list workflow without weakening weekly-plan atomicity.

The browser submits Family, Persons, ordinary slot/candidate identities and practical context. The server runs the established shared practical recommendation pipeline independently for each slot, carries the exact Person-specific Plan-Fit used for that candidate as transient internal evidence, then feeds the shared weekly optimizer. Clients never submit or own `MealPlanFitRead`, weekly progress, rule evaluation or classification evidence.

Proposal generation returns the selected combination, Person-specific portions/scores/explanations, optimization counters and each slot's recommendation engine version. A requested slot that has no server-authoritative eligible candidate is returned as an explicit pending/skipped slot and is excluded from combination search, so missing live delivery evidence cannot invalidate the rest of the week. It does not create MealEvents. Weekly acceptance/materialization is now explicit and atomic over the selected choices: the server recomputes the reviewed selection, validates candidate/transformation identity and persists all selected MealEvents in one transaction. The Week view refreshes the authoritative meal plan afterwards.

The current branch adds a derivative post-apply shopping refresh. It reuses the existing server-authoritative pantry/shopping calculation, and transformed meals contribute their persisted replacement ingredient rather than the source Recipe ingredient. Shopping refresh failure is reported separately and never implies that an already-committed weekly plan was rolled back.

ADRs:

- `docs/decisions/ADR-047-full-week-planning-consumes-meal-plan-fit-evidence.md`
- `docs/decisions/ADR-048-weekly-planning-rechecks-daily-nutrient-limits.md`
- `docs/decisions/ADR-049-shared-family-weekly-planning-reuses-person-planner.md`
- `docs/decisions/ADR-050-weekly-planning-api-is-server-authoritative.md`
- `docs/decisions/ADR-058-weekly-exact-repeat-diversity-is-soft.md`

Next Phase 8c increments after this slice include proposal acceptance/materialization, richer across-week category/protein diversity, pantry/shopping/schedule coupling and scalable search.

## Frontend information architecture

Keep progressive disclosure and focused screens:

```text
Início
Refeições
Pessoas
Casa
Mais
```

Important areas:

```text
Refeições -> Hoje | Semana | Recomendar
Casa      -> Receitas | Ingredientes | Despensa | Compras | Preferências
Pessoas   -> Visão geral | Nutrição | Atividade | Saúde | Histórico | Perfil
```

Nutrition Plan, import, Plan-Fit and weekly guidance evidence belong to the selected Person's Nutrition context; operational meal planning remains under Refeições.

## Roadmap state

```text
0. Reconfirm baseline                                                     DONE
1. NutritionPlan domain/provenance                                        DONE
2. EffectiveNutritionPlan compiler                                        FOUNDATION DONE
3. Plan import/parser + explicit confirmation                             DONE
3b. AI-assisted text interpretation + browser review                      DONE (v1)
3c. PDF/DOCX/TXT/Markdown text extraction                                 DONE (v1)
4. Meal Plan-Fit evaluation/explanations                                  DONE (v1)
5. Structured Meal Transformation proposals                               DONE (v1)
6. Home/pantry/recipe recommendations consuming Plan-Fit                  DONE (v1)
6b. Shared-family Person-specific Plan-Fit                                DONE (v1)
7. Restaurant/delivery recommendations consuming same Plan-Fit            DONE (v1)
8. Adaptive weekly planning                                               IN PROGRESS
8a. Deterministic weekly frequency progress                               DONE (v1, PR #48)
8b. Individual weekly-aware candidate selection                           DONE (v1, PR #49)
8b extension. Shared-family participant-specific weekly adaptation        DONE (v1, PR #50)
8c. Full-week multi-slot optimization                                     IN PROGRESS
8c foundation. Person-specific multi-slot weekly composition              DONE (v1, PR #51)
8c daily coupling. Same-day mandatory nutrient upper bounds               DONE (v1, PR #52)
8c shared. Shared-Family multi-slot Person-specific planning              DONE (v1, PR #53)
8c API. Server-authoritative weekly planning proposal orchestration       DONE (v1, PR #54)
8c search. Deterministic bounded search                                   DONE (v1, PR #55)
8c transformations. Safe transformed variants in weekly planning          DONE (v1, PR #66)
8c materialization. Atomic weekly application                             DONE (v1, PR #67)
8c Week UI. Monday-Sunday progressive-disclosure workflow                 DONE (v1, PR #68)
8c transformed read model. Persisted operation visible after apply        DONE (v1, PR #69)
8c shopping coupling. Refresh pantry-aware shopping after apply           IN PROGRESS
9. Feedback/learning refinement                                           PENDING
```

OCR/photo import remains a parallel capability gap, not a reason to create a second plan-import trust boundary.

## Known limitations / technical debt

- production authentication / Family authorization are not implemented;
- Family UUID remains development context;
- catalogue classification/evidence quality remains incomplete and visible;
- consumer marketplace discovery depends on provider access/configuration;
- external items without composition remain intentionally unranked;
- OCR/photo/scanned-PDF extraction is deferred;
- bounded weekly search is deterministic but can still prune the full combinatorial space;
- daily minimum completion is not forced unless complete-day slot coverage becomes explicit;
- pantry depletion, shopping and schedule coupling are not yet optimized jointly;
- richer reviewed food-category taxonomy/equivalence is deferred;
- qualitative guidance remains visible but is not automatically guessed/scored;
- unscoped recommendation still has the legacy nutrition evaluator;
- MealPlanFit still imports private candidate-loading helpers from recommendation API; extract a public common service later;
- candidate-by-candidate Plan-Fit is correct but not yet batch-optimized;
- transformation proposals are not yet persistent Recipe variants;
- production npm lockfile / `npm ci` hardening remains pending.

## Delivery workflow — ADR-007

For each functional block:

1. resolve exact `main` SHA;
2. create focused branch from it;
3. build code/tests/docs together;
4. migrations only when persistence changes;
5. warnings are failures;
6. validate GitHub Actions on the exact final PR head;
7. never rely on checks from an earlier head;
8. verify mergeability and unchanged head;
9. guarded squash merge using expected head SHA;
10. verify resulting `main` before new work.

Never use `docker compose down -v` as a routine reset because the local PostgreSQL volume may contain user-created data.

## Resume procedure

At a new session during this slice:

1. resolve current `main`, branch head, open PR and schema head;
2. confirm branch base is the verified post-PR-#53 main `70d0d344e1b0bc87233b27e88cf94088fb5d9857` unless main has legitimately advanced;
3. read this file plus ADR-044 through ADR-050;
4. verify clients submit only ordinary slot/candidate/practical inputs and never Plan-Fit or weekly progress evidence;
5. verify each shared participant retains the exact server-generated Person-specific Plan-Fit used for that candidate;
6. verify diversity/feedback adjustments preserve that transient Plan-Fit evidence;
7. verify weekly proposal generation calls the shared weekly optimizer and does not create MealEvents;
8. inspect API CI and Web CI on the exact latest PR head; warnings count as failures;
9. guarded squash-merge only after exact-head CI is green, PR head is unchanged and PR is mergeable;
10. verify post-merge `main` before starting weekly proposal acceptance/materialization.


## Review increment — NutritionPlan actionability diagnostics

Temporary review branch:

```text
fix/nutrition-plan-actionability-review
```

Base: exact PR #73 review head `723213cba0721d7b5eaae6c3e58057ca72c8a44c`. This is intentionally stacked on the unmerged integrated review branch because the affected weekly/import code is not yet on `main`. Do not merge this branch or PR #73 without explicit user review.

Confirmed production-like diagnosis from the local Loureiro data:

- Luís has an active `Plano do nutricionista` from 2026-09-18 with 40 rules and 32 guidelines;
- the effective plan for 2026-09-21 dinner reports `active_plan`;
- Mac and Cheese is `eligible=True`, `status=unknown`, `fit_score=None`, with candidate authority `partial_plan_coverage`;
- the plan is therefore persisted and loaded correctly; the apparent absence in Week UI came from downstream response loss plus unsupported rule evidence.

This increment:

- propagates Person-specific `plan_fit_status`, `plan_fit_score`, `nutrition_plan_authority`, active plan IDs/titles and unknown evidence into weekly proposal participants;
- shows the derived authority in the Week detail instead of presenting raw `unknown` as if no plan existed;
- allows explicit prohibitions to use the existing import `numeric_rule` envelope with `operator=exclude` and no numeric values/unit;
- materializes confirmed exclusions as `NutritionConstraint(constraint_type=exclusion)`;
- teaches ChatGPT-assisted import to split explicit multi-subject exclusions while preserving review/provenance;
- keeps unsupported food-category evidence unknown/not evaluated and never infers membership from recipe names/descriptions.

No database migration is introduced by this increment.

Before opening any PR, run the ADR-007 local gates on the exact branch head:

```powershell
python -m alembic check
cd apps\api
python -m ruff check .
python -m pytest -q

cd ..\web
npm install --no-package-lock --ignore-scripts
npm run test
npm run build
```

Only after those local gates are explicitly green should an integration/review PR be opened.


## Review regression fix — legacy Recipe serving normalization

Stacked review branch:

```text
fix/legacy-recipe-serving-normalization-review
```

Base: NutritionPlan actionability review head `31c5bca37b55bdf6f81e7bde55c9ade9246e7a72`.

During functional review, Mac and Cheese exposed an independent portion-sizing defect: its legacy RecipeCompositionSnapshot represented the whole recipe as `6 serving` / `5899 kcal`, while `Recipe.serving_count` was null. Planning bootstrap therefore exposed 6 servings as the candidate baseline, and automatic portion sizing could only scale that baseline by 0.5x..2x, producing impossible Person portions such as 3 or 6 servings.

The bootstrap now treats a composition whose `reference_unit=serving` as intrinsically scalable by serving count: the planning candidate baseline is 1 serving and energy is scaled by `1 / reference_quantity`. This does not mutate legacy Recipe rows or infer a missing serving_count. Non-serving snapshots retain the existing serving_count/yield behaviour.

Regression coverage includes the real legacy shape `6 serving / 5899 kcal / serving_count=None`.


## Review regression fix — weekly portion semantics and display

Stacked review branch:

```text
fix/weekly-portion-allocation-display-review
```

Base: `fix/legacy-recipe-serving-normalization-review` at `21d37867a0c3d9e32d65d5c2dc39ebf28313ca77`.

Functional review exposed two separate problems after Recipe serving normalization:

1. Weekly auto-sizing was reusing the same-day remaining-energy redistribution policy. Because future weekly slots are evaluated independently before proposed meals exist, dinner saw nearly the whole daily target as "remaining" and pushed many candidates to the 2x maximum.
2. The UI leaked persistence values such as `2.0000 serving` and machine explanation codes, making the proposal difficult to interpret.

This increment:

- preserves remaining-energy redistribution for ordinary same-day recommendations;
- uses fixed daily meal shares for weekly auto-sizing: breakfast 25%, lunch 35%, snack 10%, dinner 30%;
- versions the weekly policy as `meal-energy-allocation-v3-fixed-daily-weight` and weekly sizing as `portion-sizing-v2-weekly-fixed-weight`;
- exposes the Person-specific meal-energy reference range used to size each weekly portion;
- renders `serving` as localized Recipe portions with at most two decimals, never raw four-decimal persistence precision;
- rounds displayed kcal to whole kcal while leaving stored/calculated Decimal values unchanged;
- hides duplicate Plan-Fit machine codes already represented by the dedicated status fields;
- translates known rating, location, timing, energy and preference signals into user-facing text.

No database migration is introduced.


## Review increment — weekly nutrition comparison + explicit adaptation suggestions

Stacked review branch:

```text
feat/weekly-nutrition-comparison-adaptation-review
```

Base: `fix/weekly-portion-allocation-display-review` exact head `1f3f87fe0372480edc7254255019f378bdaea337`.

This increment makes the weekly meal detail answer two user-facing questions without recreating nutrition logic in the browser:

1. what nutrition the exact Person-specific proposed portion contains;
2. how machine-evaluable plan-backed nutrient rules compare with that portion when an active NutritionPlan provides such targets.

The weekly proposal response now carries:

- selected Recipe id when the candidate is a Recipe;
- Person-specific DailyNutritionState id;
- exact candidate nutrition used by Plan-Fit;
- compact plan-backed candidate/meal rule results relevant to nutrient/meal composition/food-category evidence.

The UI:

- shows a compact portion nutrition summary;
- shows observed vs plan target and Plan-Fit status for structured numeric nutrient rules;
- shows up to four high-priority applicable qualitative NutritionPlan instructions as context, explicitly marked as not automatically evaluated;
- explicitly says when an active plan has no quantitative evaluable target rather than inventing one from qualitative guidance;
- offers an `Adaptar ao plano` action for Recipes;
- calls the existing shared-Family transformation proposal endpoint with the reviewed Person-specific portions/state ids;
- displays safe structured substitutions and Person-specific before/after fit evidence;
- does not apply a suggested transformation automatically.

No database migration is introduced. A later increment may let the user choose one displayed transformation and re-pin/revalidate that exact structured variant inside the weekly proposal before materialization.

Validação final do incremento de auditoria: **388 testes API e 119 frontend passaram**;
TypeScript/build, Ruff completo e Alembic check passaram. Sem nova migration.

Execução focada final: 14 testes de agenda/variantes passaram, incluindo grupo com
mais de 20 pessoas e rejeição do ingrediente para o último participante.

Validação final T06: 34 API focados e 128 frontend passaram; regressão completa API 399
passou neste incremento. Build, Ruff e Alembic check passaram. Interface isolada confirmou
pré-visualização → guardar 3 embalagens → recarregar → escolha preservada. Captura local
`docs/audits/2026-10-18/confirmed-shopping-packages-interface.png`, sem publicação de dados.


### Preview UX — segundo incremento local, 18 novembro 2026

Na mesma branch `codex/ux-foundation-preview`: avatares por idade/sexo conhecido e pele comum por família na home/lista/perfil; dashboard expõe idade calculada à data e sexo opcional já persistido, sem migration. Botão Definições explícito e idempotente; refresh mantém o ecrã. Criação de pessoa com perfil energético opcional, incluindo crianças; sem GET de cálculo após criação que pudesse transformar um sucesso numa mensagem de erro. Receitas em cartões e navegação progressiva com todas as ferramentas preservadas. Sem implementação de novos modelos ML neste lote.

Verificação: 154 testes frontend, TypeScript/build, Ruff e dez testes API (dashboard, criação familiar e cálculo energético) na DB isolada passaram; API reiniciada, web HTTP200 e contrato novo confirmados por HTTP. Revisão visual e E2E de navegador permanecem pendentes. Preview continua em http://127.0.0.1:5173.


### Preview UX — terceiro incremento local, 18 novembro 2026

Avatares agora distinguem seis gerações (adulto jovem 18–29, adulto 30–44, meia-idade 45–64, além de criança/adolescente/sénior) e seis variantes. Todos os estilos masculinos de meia-idade mantêm cabelo completo; alterações visuais não são dados demográficos. Personalização visual no perfil é persistida pela API (substitui o armazenamento experimental apenas no navegador). Acrescentado `persons.avatar_appearance` JSON nullable, schema estrito e limites validados, PATCH de Person preserva o campo quando omitido e repõe automático com null. Dashboard e GET de pessoa devolvem as mesmas escolhas. Backup PostgreSQL antes da migration aditiva `c2a91f4e780d`; migration e Alembic check verificados na DB isolada antes de aplicar localmente. As quatro escolhas explicitamente solicitadas foram guardadas na família correspondente via API, sem alterar datas de nascimento ou dados energéticos.

Mais UX: entrada da família com nome primeiro e opções avançadas recolhidas; avaliações por pessoa acessíveis em detalhe de receita própria/partilhada e carregadas só ao expandir; semântica de gosto separada de adequação. Durante gravação de uma avaliação os outros controlos ficam bloqueados para evitar pedidos concorrentes.

Verificação: 155 testes frontend, build/TypeScript, Ruff, 12 testes API direcionados e migration check passaram. Verificação headless Edge sem capturar/controlar o ecrã do utilizador: quatro atribuições de avatar, consistência do perfil, seis estilos, claro/escuro, sem overflow horizontal a 1440/1024/768/390 e sem exceções JS no percurso. Capturas locais em `.cache`. Regressão API completa: 441 testes passaram em 152,30 segundos na DB de validação. Percurso de receitas verificado no navegador até ao painel contextual de avaliações das quatro pessoas, apenas leitura.


### Correção do foco horário na home — 18 novembro 2026

O destaque voltava à primeira refeição pendente do dia quando todas as horas já tinham passado, podendo mostrar um lanche às 21h. Eliminado esse fallback: usa a hora no fuso da família e mantém uma refeição pendente do período atual (ex.: jantar às 20h ainda relevante às 20h55), depois procura eventos futuros. Refeições antigas de outro período/dia não voltam ao destaque. Sem evento, a sugestão acompanha o período local: pequeno-almoço antes das 11h, almoço 11–15h, lanche 15–18h, jantar após 18h. Atualização do relógio a cada 30 segundos; não exige refresh manual. Intervalos são defaults visuais, não alteram horários ou planos guardados. Testes cobrem 20h55, jantar concluído, dia anterior, limites horários, outros fusos e horário de verão.


### Incremento semanal e cross-check contínuo — 18 novembro 2026

A pedido do utilizador, comparação explícita com o protótipo aprovado antes de fechar cada incremento, conforme `docs/ux/crosscheck-prototipo-2026-11-18.md` e direção visual atualizada. Semana com subgrid e quatro linhas alinhadas, resumo real de tempos ocupados/vazios/propostos, seleção por dia no mobile, estado resumido por célula. Espaço vazio abre o editor manual existente; cancelamento preserva dia/tempo. Detalhe mantém foco, retorno ao mapa, participantes com avatares e comparação base/alternativa com quantidade e estado; desconhecido não vira equivalência grama por grama. Restrições atuais são carregadas antes das ferramentas de adaptação; restaurante/entrega montam só ao expandir. Home com atalhos para compras/receitas.

160 testes web passaram. Verificação headless Edge com quatro larguras, alinhamento das 28 células, editor/cancelamento, trocas e retorno, claro/escuro/claro sem exceções JS nem alterações às refeições reais. API inalterada neste lote. Limitações: detalhe abaixo do mapa em vez do drawer, URLs por contexto, compras/despensa e editor de ingredientes por continuar; não foi treinado novo modelo ML. Frontend reiniciado após detetar conteúdo CSS servido antigo; conteúdo final confirmado por HTTP.


### Incremento compras/despensa — 18 novembro 2026

Checklist com pesquisa/filtros (A comprar, Comprados, Recebidos, Todos) e contagens distintas: comprar não regista stock, parcial não é receção concluída. Conferência plano/despensa e detalhes dos avisos em disclosure; presença de avisos continua visível. Embalagens só montam ao abrir; entrada na despensa mantém o componente existente com proteção de versão/idempotência. Quantidade/unidade manual validadas em conjunto; mudança de período mostra aviso sem recalcular automaticamente. Navegação direta Compras → Despensa e destino Receitas coerente ao regressar. Despensa com pesquisa por nome/local, filtros de validade, prioridade de lotes por data sem os fundir, estado sem data distinto e vazio com próximo passo. Quantidades inválidas ou vazias não seguem para gravação. Loads de lista/stock ignoram respostas após desmontagem.

167 testes frontend e build passaram. Edge headless: API real em leitura; mutações de checklist testadas com respostas sintéticas intercetadas, sem escrita em compras/stock reais. Cross-check do protótipo atualizado. Não há alteração de schema/API/ML neste incremento. A conferência de stock continua recolhida em vez da coluna lateral do protótipo; sincronização de reservas/consumo e auditoria global de acessibilidade continuam pendentes.


### Incremento maior — aceitar trocas e confirmar refeição, 18 novembro 2026

Novo `MealAdaptationFlow` integrado em `SelectedMealOptions`: três estados visíveis, preparação de várias trocas e doses reais, criação/verificação no servidor, aceitação (ativação) separada da confirmação da refeição. Ingredientes de proposta textual não são resolvidos por suposição; quantidades, unidades e preparação em falta são pedidas. Adaptações guardadas podem ser reavaliadas. A confirmação usa os endpoints reais de criar/atualizar refeição, atualiza o mapa e recalcula compras; falha nas compras não desfaz nem oculta a gravação da refeição. Incluída confirmação individual de uma proposta, materializando um único slot e invalidando as sugestões restantes para recálculo.

API: `MealPlanEntryRead.updated_at` e campo opcional `MealPlanEntryUpdate.expected_updated_at`, com comparação sob bloqueio de linha. Atualizações recebem novo token inclusive quando apenas mudam participantes/metadados; clientes antigos continuam compatíveis, mas o novo fluxo exige token para editar uma refeição guardada. Sem migration. Datas/horas são preservadas na substituição; doses confirmadas em serving, sem conversão implícita de gramas. Restrição nova ou variante inválida é reavaliada e bloqueia gravação.

Corrigido refresh que esvaziava `loadedReviews` após guardar/verificar e desmontava o fluxo, perdendo o passo atual. Contexto do novo callback de refeição confirmada é verificado antes/depois do reload da semana. Ecrã de proposta agora diz «Confirmar a semana no plano» e disponibiliza «Confirmar só esta refeição».

Verificação: 172 testes web, 444 API, Ruff e build passaram. E2E completo real (sem mocks) com PostgreSQL/API/frontend dedicados: duas trocas, verificar, aceitar sem mexer no mapa, confirmar mantendo evento/horário, nutrição esperada e ingredientes efetivos nas compras; confirmação de proposta cria só uma refeição. Quatro larguras e temas testados. Testes não escreveram refeições/compras na família principal. Preview principal reiniciada para servir o contrato novo; ficheiros de teste e capturas em `.cache`, DB de E2E separada preservada para inspeção. Instruções e cross-check em `docs/ux/aceitar-trocas-e-refeicao.md` e relatório do protótipo.


### Correção de formatação do formulário e impressão — 18 novembro 2026

O PDF enviado pelo utilizador revelou uma regressão real do formulário: `.nf-flow-edit input{width:100%}` sobrepunha a largura do checkbox e comprimia o nome do ingrediente. A regra de controlos de texto passa a excluir checkbox; checkbox com largura/flex-basis fixos e texto flexível. Grelha de campos explícita: duas colunas em desktop, uma no mobile.

Acrescentado print.css com cabeçalho de documento, remoção da navegação, margem lateral da shell anulada, sete dias sempre presentes na semana impressa, detalhe em nova página e grupos de ingrediente sem corte. PDF corrigido gerado a partir da aplicação real em leitura, sem preencher dados em falta ou alterar refeições: `output/pdf/NutriFlow-AI-corrigido.pdf`. Cinco páginas renderizadas e revistas, em comparação com oito do original. Não publicar como fixture: contém nomes da família. Verificação Edge headless: checkbox ~19px e texto >120px em 1440/1024/768/390, sem overflow; impressão mostra todos os sete dias e oculta navegação. Build/TypeScript passaram. A API não foi alterada neste lote.


### Fluxo corrigido conforme as figuras 3 → 2 → 1 — 18 novembro 2026

`SubstitutionChoices` agora é a primeira vista de «Preparar as trocas»: comparação antes/depois, aceitar/ignorar por ingrediente e manual opcional inline; pode acrescentar troca para outro ingrediente existente. Decisões são locais à receita até guardar a variante. «Aceitar escolhas e editar receita» só exige decidir todas as propostas, não dados técnicos que ainda podem ser completados na segunda etapa. Aí só aparecem operações escolhidas; a terceira confirma a refeição. Todas ignoradas também podem avançar e confirmar a receita original com as unidades preservadas; restrições obrigatórias são reavaliadas e não são ultrapassadas por ignorar.

Removida a lista duplicada de propostas fora do fluxo; o painel fica montado/oculto durante edição, preservando seleção entre várias alternativas ao voltar. Edição dos campos passa a decisão a manual, e escolher adaptação existente sincroniza escolhas/porções sem converter gramas em doses. Instruções canónicas atualizadas em docs/ux/aceitar-trocas-e-refeicao.md.

176 testes web e build passaram. E2E real em base dedicada `nutriflow_ux_choices_e2e_20261118`: aceitar/ignorar, abrir/cancelar manual, acrescentar manual, voltar, verificar receita, confirmar no servidor e impedir original incompatível após ignorar tudo; quatro larguras e temas. Na família principal só navegação/seleção local, sem persistir alterações alimentares. A API não foi alterada neste lote; regressão de 444 testes continua a ser a do lote anterior. Preview principal reiniciada e verificada.


### Resumo da receita preenchida e avanço único — 18 novembro 2026

Segunda etapa passa de edição obrigatória a revisão: preview mostra alternativas aceites, quantidades, preparação e doses conhecidas. `acceptedNames` conserva a descrição da proposta mesmo sem ID de catálogo; o seletor em falta mostra o nome a associar em vez de o perder. Edição completa opcional com valores preenchidos; apenas dados em falta são mostrados automaticamente. Doses deixam de reinicializar ao regressar às escolhas sem mudar entre receita original e variante. `SubstitutionChoices` comunica a descrição explícita da alternativa escolhida.

«Seguir para confirmação final» agrega criação de rascunho, validação e ativação existentes; não altera a refeição antes da confirmação final. Removidos «Guardar e verificar receita» / «Aceitar receita e continuar» como duas ações intermédias. Sem trocas usa o mesmo avanço, preservando a revalidação de restrições. API inalterada.

176 testes frontend/build passaram. E2E real em DB dedicada `nutriflow_ux_review_e2e_20261118` verifica preenchimento, campos em falta, valores ao editar, avanço único, confirmação de refeição, modo totalmente preenchido sem editor obrigatório, temas/quatro larguras e bloqueio de original incompatível. Família principal não teve receitas/refeições alteradas. Instruções canónicas atualizadas.


### Pendências herdadas não bloqueiam a revisão final — 18 novembro 2026

O ficheiro do utilizador mostrava base sem serving_count e duas propostas sem ingredientes de catálogo/quantidades/unidades. Separado avançar na revisão de aplicar uma variante: Next permanece disponível, lista pendências concretas e oferece guardar rascunho. Missing yield é explicitamente identificado como não registado na fonte. Não se inventam doses, equivalências ou composição. Caminho completo continua a usar os serviços rigorosos de variantes; snapshot parcial nunca é ativo ou planeável.

Nova tabela `meal_adaptation_drafts` (migration d9a704c281e6), snapshots parciais, CRUD criar/listar/atualizar com família/receita/ingredientes/pessoas/refeição validados, versão esperada em atualizações e fingerprint da base. Sem endpoint de ativação. Frontend guarda e retoma escolhas e texto com null/vazios; refeição e compras mantêm-se intactas. Migration/check/testes direcionados passaram na DB isolada antes de migrar localmente. Backup prévio `backups/ux-before-pending-drafts-20261118.dump`. Nenhuma escolha de alimentação foi alterada na base principal.

177 testes web/build e E2E real em DB dedicada passaram: campos herdados ausentes, Next disponível, save/reload/resume, nenhum RecipeVariant criado e evento original inalterado; quatro larguras. Preview principal com rota nova reiniciada e verificada em leitura. Regressão API completa: 447 testes passaram na DB de validação. Ruff passou. Instruções canónicas e cross-check atualizados.


### Campos estáveis e trocas opcionais na revisão — 18 novembro 2026

Corrigido desaparecimento durante escrita: modo de edição explícito mantém campos montados até fechar, incluindo quando todos ficam válidos. Quantidade/unidade da base usadas como ponto de partida editável; proposta explícita tem prioridade e mudança de unidade sem quantidade não converte automaticamente. Preparação conhecida exposta na API de revisão e copiada. Segunda etapa oferece acrescentar qualquer ingrediente ainda sem troca, por preferência, sem exigir restrição. Não altera o catálogo ou receita original.

Cross-check: três etapas, resumo progressivo e tokens aprovados preservados; editor completo abre quando há pendências e fecha explicitamente. 178 testes web, build/TypeScript, Ruff e 35 testes API direcionados passaram na DB isolada. Navegador real headless, API real principal em leitura: quantidade inicial 1 un, escrita de 125 e preparação sem perder campos, troca adicional na segunda etapa, quatro larguras sem overflow/erros JS; sem gravar refeições/receitas da família. Servidores locais reiniciados.


### Confirmação sem pendências artificiais — 18 novembro 2026

Preparação deixa de ser obrigatória no contrato de variantes e no frontend. Aceitar proposta sem ingrediente concreto resolve apenas correspondência exata única no catálogo; caso contrário abre imediatamente a escolha concreta, conservando quantidade/unidade. Avanço incompleto mantém revisão editável com faltas precisas, sem a antiga etapa final genérica. Rendimento existente é herdado; não se inventa rendimento ausente. Estado confirmado deriva do recipe_id de uma refeição persistida e variante ativa, nunca de aceitação local. Ocultadas propostas/formulário da base depois de aplicar; edição explícita recupera variante atual. Restrições/composição continuam verificadas pelo servidor.

180 testes frontend, build, Ruff e 36 testes API direcionados passaram em DB isolada. E2E real dedicado: proposta textual pede associação, nome exato resolve ID, preparação vazia permite criar/validar/ativar/aplicar, reload mantém estado confirmado sem propostas base e editar recupera operações; quatro larguras sem overflow ou erros JS. Base principal sem alterações a refeições/receitas.


### Regressão de aceitação direta corrigida — 19 novembro 2026

Repõe o fluxo aprovado: Aceitar proposta regista accepted imediatamente e não abre edição manual, mesmo sem ID concreto. Mantém associação automática apenas por nome exato único, valores de base e preparação opcional. Se a edição manual do mesmo ingrediente estiver aberta, aceitar/ignorar fecha-a. Identificação ainda desconhecida conserva a descrição na revisão da receita, sem inventar alimento nem modificar validação de aplicação.

181 testes frontend e build/TypeScript passaram. E2E real headless na app principal, em leitura: edição manual aberta explicitamente, aceitar fecha-a; duas propostas aceites sem formulário; passo 2 disponível; nomes/quantidades preservados; escrita de vários algarismos e navegação de volta conservadas. Nenhuma refeição/receita gravada. Servidor web reiniciado.


### Edições herdam requisitos da receita original — 19 novembro 2026

Separada edição aprovada pela família de variante nutricional validada. Novo POST recipe-variants/recipe-edit permite rendimento ausente, unidades existentes (emb), preparação ausente e descrições aceites sem ID prévio; descrições geram ingrediente privado da família sem composição fabricada. Quantidades/porções/unidades herdadas; referência de porção existente preservada sem copiar nutrientes da base. source family_adaptation e confirmation_mode recipe_edit distinguem estas edições; workflow ativo não certifica nutrição. Não há migration: usa receitas/ingredientes/FamilyRecipeVariant e evidência JSON existentes.

Aplicação verifica propriedade da família, ingredientes disponíveis, base/evidência intactas, meal type e restrições ativas conhecidas, como a base. Desconhecido nutricional fica nulo, não um valor herdado. Ativação/validação de variantes rigorosas mantém contratos existentes. Reviews incluem edições aplicadas válidas para mostrar confirmação sem repetir pendências da base. Base principal sem alterações a refeições/receitas durante testes.

Cross-check com protótipo: aceitar direto → resumo editável opcional → confirmação; nenhum campo novo obrigatório para dados ausentes na base, mais trocas opcionais mantidas. E2E real dedicado (DB nutriflow_ux_inherit_e2e_20261119): yield nulo, emb, descrições sem ID, aplicação e compras, nutrientes nulos, porções originais, reload confirmado e edição recuperada; quatro larguras sem overflow ou JS errors. 182 testes frontend/build, Ruff e 17 testes API direcionados passaram. Regressão API completa: 452 testes passaram na DB isolada. Teste direcionado adicional confirma que a edição aparece nas reviews mesmo com nutrição desconhecida. Percurso Frango de quinta-feira na app principal verificado em leitura: aceitar direto, emb/quantidades herdadas, sem editor obrigatório ou bloqueio por rendimento/ID ausente.


### Lote de 20 tarefas de navegação e autoria — 19 novembro 2026

Checklist/evidência canónicos: `docs/ux/lote-20-2026-11-19.md`, 20/20 locais. Navegação por hash com contexto de pessoa, separador, data e modo, back/forward; filtros de receitas por família/tempo/origem, ordenação, contagem e limpeza, em detalhe progressivo; cópia editável da receita com original intacto, dados opcionais preservados, pesquisa e IDs estáveis nas linhas. Guardas de alterações por guardar nas receitas/refeições, incluindo navegação e unload; identidade/quantidades preservadas em cancelar. Editor de refeição com avatares, presença em lote, pesquisa e resumo antes de guardar, mais versão esperada no update.

188 testes frontend, TypeScript/build passaram. E2E real dedicado guardou cópia e refeição sintéticas; URL/reload/back/forward, filtros, guardas, reordenação, quatro resoluções/temas/foco e ausência de JS exceptions passaram. Regressão real do percurso de adaptação também passou. Sem alterações API/migrations neste lote; a suíte API de 452 do incremento anterior não foi repetida sem alterações de backend. Dados principais não foram alterados. Protótipo HTML consultado; paletas e cinco destinos mantidos, filtros móveis recolhidos. Servidor web reiniciado para preview final.
