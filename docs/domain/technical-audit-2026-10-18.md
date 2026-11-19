# Auditoria técnica transversal — 18/10/2026

## Âmbito e método

Apenas v2. Revisão estrutural dos módulos de interface, rotas, modelos e migrações;
inventário PostgreSQL completo em `schema-audit-2026-10-18.md`. Verificação manual
no navegador dos percursos início → semana → prato e compras. Os restantes módulos
foram inventariados e revistos no código; não se afirma teste manual exaustivo de cada
formulário, dispositivo ou serviço externo. Testes isolados não usam a base da família.

## Resultado e correções

| Área | Resultado | Ação |
| --- | --- | --- |
| Início e agenda | Semanas guardadas e trocas visíveis; originais com propostas continuam identificados como não aplicados | Manter diferença proposta/aplicada em todos os resumos |
| Compras | Associa alternativas aos ingredientes efetivos; faltam escolha de embalagens e total por loja | Dados de retalho limpos ao mudar família; sem assumir troca 1:1 |
| Acessibilidade de compras | Campos manuais sem nome explícito e botões repetidos | Acrescentados nomes acessíveis e ingrediente no nome de editar/remover |
| Carregamento inicial | Compras carregadas mesmo sem abrir ecrã | Separado por importação lazy com estado acessível de carregamento |
| Produtos/ingredientes | Associação percorria todo o catálogo para cada produto | Índice em memória por catalog_key; mantém isolamento familiar |
| Evidência de produtos | Ingredientes publicados eram confundidos com rótulo desconhecido | Novo nível ingredientes publicados/nutrição desconhecida, com teste |
| Qualidade nutricional | Farinha Auchan apresenta zeros online em todos os nutrientes | Nutrição não importada; nenhum zero convertido em composição válida |
| Retalho | Apenas quatro observações | Onze produtos, com URL/data/embalagem e evidência; sete novos |
| Publicação | Backups/exportações/capturas podiam entrar por git add global | Ignorados; mudanças revistas antes de publicar |

Build: bundle JS principal passou de 470,51 kB para 430,53 kB (gzip 133,04 →
122,19 kB). A redução é do carregamento inicial; não significa redução do código total.

## Base de dados

52 tabelas de aplicação + Alembic; todas inventariadas. Alembic check sem divergências.
Inspeção PostgreSQL: zero constraints não validadas e zero índices inválidos. Saúde,
variantes e semana têm unicidade/versão; variantes preservam receitas históricas.
Presenças em JSON têm validação da aplicação e não FK interna para cada elemento.

Foram encontradas 24 FK sem índice com as mesmas colunas à esquerda, sobretudo em
recomendações, transformações e referências. Isto é uma oportunidade de medição,
não prova de lentidão. Evitou-se criar 24 índices sem EXPLAIN/volume representativo.
Próximo passo: medir consultas de recomendações, lotes e revisão alimentar e só então
adicionar índices justificados, com migration e verificação de escrita/armazenamento.

## Pendências prioritárias

1. **P0 antes de deployment público:** autenticação e autorização de utilizadores.
   Atualmente os endpoints validam pertença familiar de entidades mas não a identidade
   do utilizador. Manter uso local; não publicar o serviço de saúde na Internet assim.
2. **P1:** padrões reutilizáveis de presenças, incerteza e refeições individuais no percurso.
3. **P1:** revalidar escolhas fixadas ao alterar presentes/restrições, com explicação e confirmação.
4. **P1:** escolher embalagem/marca e calcular quantidades só após variante validada.
5. **P1:** versões/fases de dietas e tolerâncias por pessoa com validade explícita.
6. **P2:** normalizar componentes muito compactos, unificar erros e melhorar manutenção;
   cache/paginação da revisão de receitas após medir com catálogo maior.
7. **P2:** sobras, consumo e feedback ligados ao planeamento seguinte.
8. **Dependência externa:** menus Uber/Glovo/Bolt requerem acesso adequado; conta normal
   permite links ao serviço, não importação automática garantida.

## Inventário de componentes de interface

- `App.tsx`
- `DeliveryMenuScreen.tsx`
- `FamilyEntryScreen.tsx`
- `FamilyHome.tsx`
- `FamilyMeals.tsx`
- `FamilySettings.tsx`
- `HomeBase.tsx`
- `IngredientAlternativeLine.tsx`
- `IngredientCatalogue.tsx`
- `MealConsumptionControls.tsx`
- `MealDiscoveryCapabilitySummary.tsx`
- `MealDiscoverySettings.tsx`
- `MealPlanFitPanel.tsx`
- `MealPlanner.tsx`
- `MealSourceOptions.tsx`
- `NutritionPlanAuthorityCard.tsx`
- `NutritionPlanDocumentPicker.tsx`
- `NutritionPlanImportPanel.tsx`
- `PantryScreen.tsx`
- `PersonHealthConditions.tsx`
- `PersonMealDiscoveryOverrides.tsx`
- `PersonOverview.tsx`
- `PersonProfileEditor.tsx`
- `PersonSetupForm.tsx`
- `PlanningJourney.tsx`
- `RecipeAdaptationCards.tsx`
- `RecipeCatalogue.tsx`
- `RecipeDietaryReview.tsx`
- `RecipePreferences.tsx`
- `RecipeVariantEditor.tsx`
- `RecommendationNutritionBudget.tsx`
- `RecommendationPlanner.tsx`
- `RestaurantDiscoveryScreen.tsx`
- `RetailAlternativeCards.tsx`
- `SavedMealChanges.tsx`
- `ScheduledWeeks.tsx`
- `SelectedMealOptions.tsx`
- `SharedTransformationPreview.tsx`
- `ShoppingListScreen.tsx`
- `WeeklyProposalPreview.tsx`
- `i18n.tsx`
- `main.tsx`
- `theme.tsx`

## Validação

- Consolidação anterior: 387 testes API, 118 web e CI API/Web do commit 5aab9e3 passaram.
- Incremento de auditoria: 14 testes workspace/retalho e 119 web passaram.
- Build/TypeScript, Ruff completo e Alembic check da base local passaram.
- Interface real: compras carregadas por lazy, campos com nomes acessíveis e quatro
  alternativas de espessantes expandidas na linha da farinha. Nenhuma compra marcada
  ou refeição modificada; captura preservada apenas localmente.
- Reimportação local acrescentou zero produtos: idempotência confirmada.

Validação final do incremento de auditoria: **388 testes API e 119 frontend passaram**;
TypeScript/build, Ruff completo e Alembic check passaram. Sem nova migration.
