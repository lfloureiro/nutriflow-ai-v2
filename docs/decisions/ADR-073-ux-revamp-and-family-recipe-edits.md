# ADR-073 — UX aprovado e edição familiar de receitas

## Estado
Aceite nesta entrega, 19 novembro 2026.

## Decisão

Reutilizar serviços/domínio reais sob o UX aprovado NutriFlow AI / Casa à Mesa. O protótipo define linguagem visual e progressão, não substitui cálculos/autoridade do backend.

Distinguir edição aprovada pela família (family_adaptation, confirmation_mode recipe_edit) de variante nutricional validada (family_variant). Uma edição herda rendimento ausente, preparação opcional, unidades como emb e porções da original; mantém quantidades explícitas da proposta quando fornecidas. Descrição aceite sem catálogo é preservada como ingrediente declarado privado, sem composição ou verificação de rótulo inventadas.

A confirmação regista a escolha e aplica a receita à refeição; não certifica nutrição/FODMAP. Restrições ativas conhecidas, âmbito familiar, evidência alterada, disponibilidade e concorrência continuam verificadas. Não herdar nutrientes da original para ingredientes trocados. Desconhecido permanece nulo; compras herdam a referência de porção disponível sem conversões inventadas. Snapshots/base/outras refeições não são reescritos.

Propostas aceites não abrem editor manual. Rever receita tem edição opcional e permite trocas por preferência. Confirmar no plano atualiza estado e compras; dados originais ausentes não viram novos requisitos obrigatórios. Rascunhos incompletos têm armazenamento próprio e não são variantes certificadas.

## Validação e continuidade

188 testes web e 452 API no baseline, migrations e E2E sintético nos percursos descritos em docs/handoff-2026-11-19.md. Este ADR não declara concluídos ML treinado, conectores externos, autenticação ou toda a equivalência ao protótipo. Prosseguir pelo handoff e quadro UX.
