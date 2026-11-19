# Inventário técnico do esquema — 2026-10-18

Sem linhas de dados pessoais. Inspeção PostgreSQL e metadados SQLAlchemy.

| Tabela | Colunas | FK | Índices | Unique |
| --- | ---: | ---: | ---: | ---: |
| `alembic_version` | 1 | 0 | 0 | 0 |
| `anthropometric_measurements` | 12 | 1 | 1 | 0 |
| `daily_health_states` | 23 | 1 | 2 | 1 |
| `daily_nutrition_state_components` | 11 | 1 | 2 | 1 |
| `daily_nutrition_states` | 17 | 2 | 2 | 1 |
| `families` | 8 | 0 | 0 | 0 |
| `family_recipe_variants` | 15 | 3 | 4 | 2 |
| `family_week_setups` | 7 | 1 | 1 | 1 |
| `fodmap_references` | 16 | 0 | 1 | 1 |
| `food_adverse_reactions` | 15 | 1 | 1 | 0 |
| `food_composition_snapshots` | 12 | 1 | 2 | 1 |
| `food_fodmap_references` | 6 | 2 | 1 | 1 |
| `food_items` | 13 | 1 | 3 | 1 |
| `food_nutrient_components` | 7 | 1 | 2 | 1 |
| `food_preferences` | 12 | 1 | 1 | 0 |
| `food_transformation_profiles` | 11 | 2 | 2 | 1 |
| `health_connections` | 16 | 1 | 2 | 1 |
| `health_measurements` | 22 | 2 | 4 | 1 |
| `meal_candidate_availability` | 16 | 3 | 3 | 0 |
| `meal_candidate_planning_profiles` | 13 | 3 | 3 | 2 |
| `meal_commercial_offers` | 19 | 2 | 3 | 1 |
| `meal_events` | 17 | 2 | 3 | 1 |
| `meal_participants` | 7 | 2 | 3 | 1 |
| `meal_recommendation_feedback` | 9 | 2 | 1 | 0 |
| `meal_recommendation_options` | 21 | 5 | 3 | 1 |
| `meal_recommendation_runs` | 9 | 2 | 1 | 0 |
| `meal_source_opening_windows` | 13 | 1 | 1 | 0 |
| `meal_transformation_applications` | 22 | 6 | 3 | 1 |
| `nutrition_constraints` | 19 | 1 | 1 | 0 |
| `nutrition_goals` | 12 | 1 | 1 | 0 |
| `nutrition_plan_guidelines` | 19 | 1 | 1 | 0 |
| `nutrition_plan_import_proposals` | 30 | 3 | 2 | 1 |
| `nutrition_plan_import_sessions` | 10 | 2 | 2 | 1 |
| `nutrition_plan_rules` | 14 | 4 | 4 | 0 |
| `nutrition_plans` | 15 | 2 | 3 | 1 |
| `nutrition_target_components` | 10 | 1 | 2 | 1 |
| `nutrition_targets` | 18 | 2 | 2 | 0 |
| `pantry_stock_lots` | 15 | 2 | 3 | 1 |
| `person_health_condition_events` | 6 | 1 | 1 | 1 |
| `person_health_conditions` | 13 | 1 | 2 | 1 |
| `person_profiles` | 11 | 1 | 0 | 0 |
| `persons` | 9 | 1 | 1 | 0 |
| `recipe_composition_snapshots` | 11 | 1 | 2 | 1 |
| `recipe_ingredients` | 10 | 2 | 2 | 0 |
| `recipe_nutrient_components` | 7 | 1 | 2 | 1 |
| `recipe_substitution_reviews` | 14 | 4 | 2 | 1 |
| `recipes` | 14 | 1 | 2 | 1 |
| `retail_alternatives` | 17 | 0 | 1 | 1 |
| `schedule_entries` | 20 | 1 | 1 | 0 |
| `serving_nutrition_components` | 9 | 1 | 2 | 1 |
| `servings` | 24 | 5 | 6 | 0 |
| `shopping_list_items` | 14 | 2 | 3 | 1 |
| `shopping_lists` | 12 | 1 | 2 | 1 |

## Revisão de integridade

- Saúde: unicidade pessoa/código, versões e eventos; estado/origem/datas validados.
- Variantes: unicidade receita e linhagem/revisão, FK RESTRICT para receitas históricas, bloqueio na ativação e fingerprints.
- Semana: unicidade família/segunda-feira e concorrência por versão; presenças em JSON validadas na aplicação.
- Retalho: chave única, embalagem positiva e preço não negativo; valores observados não são stock em tempo real.
- Índices não foram adicionados sem evidência de lentidão; medir EXPLAIN com volume representativo antes de otimizar planos SQL.
- Os testes usam exclusivamente uma base separada; Alembic check sem diferenças.

## Evolução após o inventário — ADR-069

Head `93c8e18311c4`: 53 tabelas de aplicação, mais `alembic_version`.
Acrescentada `retail_ingredient_confirmations` (9 colunas, 3 FK, 2 unicidades e índice
por produto), e 3 colunas em `shopping_list_items`: versão, FK de confirmação e snapshot
JSON da escolha. Versão positiva validada por CHECK; FK nomeada para downgrade reversível.
Índice por confirmação protege referências de compras. Alembic check sem diferenças.
O inventário acima conserva o snapshot inicial da auditoria, anterior a esta migration.


### Delta ADR-070 — b781e265c904

Uma coluna JSON nullable `shopping_list_items.pantry_receipt` preserva a entrada real
e a referência histórica ao lote. Total mantém 53 tabelas aplicacionais + Alembic.
Sem novos índices: procura pelo PK do artigo e unicidade de stock_key já existentes.
Bloqueio transacional e unicidade do lote impedem repetição da entrada.


### Delta ADR-071 — preço de comparação derivado

Sem alteração de tabela/índice/migration. Campo `price_comparison` acrescentado ao modelo
de leitura das observações, calculado com Decimal e unidades físicas conhecidas. Sem
preço normalizado persistido, sem consultas por linha adicionais. Head b781e265c904.


### Delta ADR-072 — entregas e avaliação temporal do stock

Sem migration/tabela/índice. Snapshot JSON existente suporta formato 2 com eventos de
receção, estado, esperado e restante. Até 32 entregas de 20 lotes, com fecho sem produtos
permitido mesmo no limite. Chaves únicas de stock e bloqueio de lista/artigo continuam
a proteger a transação. Flush explícito compatível com sessões `autoflush=False` antes
de recarregar dados. Necessidades por data/hora e orçamento FEFO são calculados sem
movimentos persistidos. Um livro de movimentos separado permanece futuro para inventário
mais extenso. Head b781e265c904; 53 tabelas aplicacionais.
