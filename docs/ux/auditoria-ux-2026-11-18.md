> Referência de continuidade: [estado atual e próximas tarefas](../handoff-2026-11-19.md). Registos intermédios abaixo são históricos; o fluxo atual está em aceitar-trocas-e-refeicao.md.

# Auditoria do UX e preparação da transformação do NutriFlow AI

18 novembro 2026. Auditoria de código, documentação, estado Git e verificações técnicas. A experiência de referência é o protótipo aprovado hoje: **NutriFlow AI**, com **Casa à Mesa** como subtítulo.

O NutriFlow tem uma base funcional mais rica do que o protótipo, mas a interface distribui decisões relacionadas por demasiados ecrãs e detalhes. A transformação deve preservar os serviços e trazer para a aplicação real a hierarquia visual, navegação por tarefas, painéis de decisão e fluidez do protótipo. Copiar o HTML demonstrativo como nova aplicação faria perder capacidades e validações existentes.

O [quadro de tarefas](../vision/ux-revamp-task-board.md) define a execução. A [especificação visual e de interação](nutriflow-design-direction.md) fixa os critérios comuns, incluindo avatares e movimento.

## 1. Estado que foi efetivamente auditado

| Superfície | Estado observado |
|---|---|
| GitHub `main` | `2d93327a169d691fe4dd5f566da94603ac09a406` |
| `origin/main` local | Mesmo SHA de `main` no GitHub |
| Branch local | `codex/health-conditions-fodmap-review` |
| HEAD local e head remoto do PR #74 | `e34d9e0f5ad7cebeb76c06035cd0cdfd33830eab` |
| `main` local | `68ed57b16b2bf021d6aae44bb56a6b9459ba3b9b`, 24 commits atrás de `origin/main` |
| Relação branch / `origin/main` | 212 commits na branch após o ancestral `2d93327…`; nenhum commit exclusivo de `origin/main` nessa comparação |
| Trabalho por integrar | PRs #70, #71, #72, #73 e #74 abertos, todos em rascunho |
| Ficheiros já modificados antes da auditoria | Três ficheiros `apps/api/nutriflow_api.egg-info/*` e `apps/web/package-lock.json` não rastreado; preservados |
| Protótipo de referência | `artefacto local aprovado Casa_a_Mesa_Prototipo.html (não versionado)`, mais as fontes em `casa-a-mesa-v4/` |

Fingerprint SHA-256 da referência visual no momento da auditoria: `35dbd5df15ee2a50a71079e3d89b06a3b4e5a73eec636712a2d2be2b3d86aada`. Alterações posteriores ao HTML precisam de ser incorporadas explicitamente no contrato de design.

PRs observados:

- [#70](https://github.com/lfloureiro/nutriflow-ai-v2/pull/70): atualização de compras após aplicar uma semana.
- [#71](https://github.com/lfloureiro/nutriflow-ai-v2/pull/71): importação assistida por ChatGPT.
- [#72](https://github.com/lfloureiro/nutriflow-ai-v2/pull/72): aplicabilidade de orientações obrigatórias.
- [#73](https://github.com/lfloureiro/nutriflow-ai-v2/pull/73): revisão de integração semanal e planos ativos.
- [#74](https://github.com/lfloureiro/nutriflow-ai-v2/pull/74): integração familiar, restrições, alternativas e compras.

Esta lista não autoriza um merge sequencial dos cinco PRs. A branch mais avançada reúne trabalho empilhado; é preciso rever ancestralidade, diferenças e estratégia de integração para não duplicar alterações.

### Capacidade existente não significa capacidade integrada em main

`WeeklyProposalPreview`, `RecipePreferences` e `NutritionPlanImportPanel` já existem em `main`. `PlanningJourney`, `PersonHealthConditions`, `RecipeVariantEditor`, `ShoppingProductChoice`, `ShoppingReceiptEntry` e `RetailComparisonTable` existem na branch auditada e não em `main` nesse checkpoint.

Por isso, o backlog usa **existente na branch**, **parcial**, **por desenvolver** e **dependência externa**, em vez de chamar tudo concluído ou tudo em falta.

## 2. Verificações realizadas e limites

| Verificação | Resultado desta auditoria |
|---|---|
| `npm run test` | **147 testes, 33 ficheiros, todos passaram** |
| `npm run build` | TypeScript e Vite passaram |
| `python -m ruff check apps/api` | Passou |
| CI API no HEAD `e34d9e0…` | Sucesso confirmado no GitHub |
| CI Web no mesmo HEAD | Sucesso confirmado no GitHub |
| Base de dados local | Tentativa de inspeção só de leitura sem ligação disponível; consulta com timeout limitado devolveu `OperationalError` |
| `alembic current` local | Não concluiu a ligação; execução interrompida. Não foi executada migration |
| Regressão API local completa | Não reexecutada, pois depende da base de dados; não se usou a base da família para testes |
| Esquema da branch | Documentação/migrations indicam `b781e265c904`; não confirmado na base ativa nesta auditoria |
| Testes visuais / navegador / capturas | Não executados nesta auditoria. Não foi iniciada sessão de captura ou controlo do ecrã |
| Serviços externos e preços | Sem chamadas a fornecedores; não se verificaram credenciais, conectividade, preços atuais ou permissões de consumidor |

CI consultado: [Web](https://github.com/lfloureiro/nutriflow-ai-v2/actions/runs/39170470423) e [API](https://github.com/lfloureiro/nutriflow-ai-v2/actions/runs/39170470384). Os 438 testes API referidos no histórico são um resultado documentado anterior, não uma execução local nova desta auditoria.

O build produziu JS principal de **431,13 kB / 122,39 kB gzip**, CSS principal de **87,21 kB / 14,21 kB gzip**, além de chunks separados. São dimensões de build, não métricas de experiência real ou prova de lentidão.

## 3. Achados prioritários

### A01. A identidade visual aprovada ainda não está na aplicação

**Prioridade P1.** `apps/web/src/styles.css` mantém o tema escuro verde (`--bg: #101611`, `--accent: #91b991`) e fundos com gradientes. O protótipo aprovado usa claro marfim/verde e escuro carvão/cinza quente/âmbar. `App.tsx` usa um monograma N e símbolos de texto na navegação; ainda não reproduz o desenho aprovado.

**Ação:** tokens semânticos para ambos os temas, tipografia, ícones SVG, marca NutriFlow AI / Casa à Mesa e componentes comuns. Não fazer uma sucessão de overrides sobre `visual-polish.css`.

### A02. Navegação e estado da tarefa precisam de um contrato único

**Prioridade P1.** `App.tsx` seleciona vistas por estado React e renderização condicional; não existe contrato de URL para pessoa, semana, receita e painel. Abrir o menu de planeamento volta ao modo semana. Componentes desmontados podem perder estado local não persistido; é um risco a cobrir com testes de navegação, não um bug de todos os formulários já reproduzido.

`HomeBase.tsx` reúne nove destinos secundários, incluindo receitas, substituições, ingredientes, despensa, compras, preferências, fontes, restaurantes e entrega. A ação central de decidir uma refeição distribui-se por vários destes destinos.

**Ação:** shell e URLs estáveis, preservação de contexto e rascunhos, receitas como destino operacional direto e fontes externas dentro do contexto da refeição. Ferramentas técnicas podem permanecer secundárias.

### A03. Criar uma pessoa continua a exigir informação que o backend já permite adiar

**Prioridade P1.** `PersonSetupForm.tsx` exige nascimento, altura, peso e estimativa do pequeno-almoço; envia sempre `energy_profile` e pede imediatamente a estimativa energética. O cálculo automático é limitado a adultos. Em contraste, `PersonCreate` já aceita `birth_date` e `energy_profile` opcionais.

**Ação:** criar primeiro a pessoa e necessidades essenciais; dados físicos e cálculo energético num segundo passo opcional. Permitir crianças na família sem aplicar fórmulas para adultos. Não remover a funcionalidade de cálculo que já existe para quem a quer usar.

### A04. O planeamento partilhado ainda não cobre toda a rotina familiar

**Prioridade P1.** Já existem presenças por slot e cópia/repetição de organização. Contudo, `PlanningJourney.tsx` e `WeeklyProposalPreview.tsx` exigem pelo menos duas pessoas no percurso de geração; refeições individuais são remetidas para a agenda manual. A configuração usa participantes por slot, mas não modela toda a experiência de padrões nomeados, presença incerta e vários grupos com locais diferentes.

**Ação:** resolver presença por refeição/grupo, suportar uma pessoa ou várias no mesmo percurso e explicitar incerteza. Não repetir uma lista familiar global nos 28 slots. Revalidar escolhas fixadas quando o contexto muda.

### A05. Uma política alimentar configurada está codificada por condição

**Prioridade P1.** `planning_restrictions.py` contém `CONDITION_PROFILES = {"sibo": "low_fodmap"}`. O comentário identifica uma política solicitada pela família e não uma prescrição universal. A interface mostra a origem automática. Mesmo assim, essa política está no código e o novo UX precisa de distinguir claramente condição registada, preferência de planeamento, protocolo revisto e regra profissional ativa.

**Ação:** tornar a política explícita, versionada e confirmável por pessoa/família, com validade, fase e tolerâncias quando fornecidas. Preservar comportamento configurado durante a migração; não o remover ou transformar em recomendação clínica silenciosamente.

### A06. Variantes completas já existem e devem ser aproveitadas

**Prioridade P1 para migração, não reconstrução.** `recipe_variant.py`, `RecipeVariantEditor.tsx` e rotas de variantes já permitem operações completas, validação, ativação e retirada. `SharedTransformationPreview` e a semana já ligam alterações ao plano. Reproduzir apenas a troca demonstrativa do HTML eliminaria capacidades reais.

**Ação:** painel único de problema → comparação → proposta/edição → avaliação por participante → aceitação. Diferenciar rascunho, revisto, ativo, aplicado e desatualizado. Preservar receita base, proveniência, snapshots e concorrência.

### A07. Compras está mais avançado do que o protótipo

**Prioridade P1 para apresentação.** Já existem ingredientes efetivos das variantes, comparação contextual de loja, embalagens, produtos confirmados, comprado/recebido, entregas parciais, vários lotes e stock com validade à data da refeição.

**Ação:** apresentar primeiro uma lista simples; produto, loja, embalagem e receção em painéis progressivos. Não reduzir estas capacidades a um checkbox. Distinguir fisicamente disponível, previsto por receber e ainda por comprar.

### A08. Há infraestrutura de IA, mas ainda não um recomendador ML treinado demonstrado

**Prioridade P1 académica e de produto.** Importação de orientações usa saída estruturada e revisão, com caminhos de API e assistência ChatGPT. O módulo `recommendation_feedback_learning.py` aplica pesos fixos a accepted/modified/rejected e recência. Isto é adaptação heurística a feedback; não demonstra treino, conjunto de teste, métricas ou generalização de um modelo ML. Não foi encontrada uma implementação de embeddings, OCR ou importação geral de receitas por URL nos módulos revistos.

**Ação:** manter o que existe como baseline, implementar conjuntos anotados, extração NLP de receitas, correspondência semântica, treino e avaliação de ranking. Mostrar estados de confiança e limites no UX; não apresentar precisão ou aprendizagem fictícias.

### A09. O mapa existe, mas a experiência unificada ainda é parcial

**Prioridade P2.** `RestaurantDiscoveryScreen.tsx` já apresenta mapa OSM incorporado e seleção da lista. `restaurantMap.ts` centra o mapa num local selecionado. Não corresponde ainda a uma exploração única e completa de fontes, pratos, vários marcadores e contexto da refeição. Interfaces e capabilities de entrega não equivalem a acesso real autorizado a todos os marketplaces.

**Ação:** pesquisa por refeição com fontes coerentes, lista/mapa sincronizados e falhas independentes. Separar local encontrado, prato real sem evidência e prato avaliado. Preservar participantes, zona, data e filtros ao alternar.

### A10. Estilo e componentes precisam de redução de acoplamento

**Prioridade P1 para viabilizar o revamp.** Inventário local: 52 ficheiros TSX, 23 CSS com 5.856 linhas. Maiores componentes: WeeklyProposalPreview 1.701 linhas, RecommendationPlanner 1.181, RecipeCatalogue 915, FamilyMeals 793. `main.tsx` importa 16 folhas CSS globais, além de folhas carregadas por componentes. `packages/ui` ainda contém apenas `.gitkeep`.

**Ação:** extrair gradualmente componentes de apresentação e hooks de dados, mantendo serviços e contratos; centralizar tokens e primitivas. O tamanho é um indicador de manutenção e risco de regressão, não um bug de desempenho comprovado.

### A11. Avatares e movimento ainda não correspondem ao objetivo

**Prioridade P1 visual.** Os membros usam iniciais estáticas em `.member-avatar`. Existem transições CSS pontuais; não foi encontrada política `prefers-reduced-motion` nas folhas CSS da aplicação auditadas nem sistema de estados de avatar.

**Ação:** avatares leves com identidade persistente e estados selecionado, participante, por confirmar e alteração concluída. Microanimações curtas e contextuais, com alternativa estática e sem representar informação clínica por expressões da personagem. A especificação própria define duração, amplitude e gatilhos.

### A12. Testes existentes não substituem testes dos percursos reais

**Prioridade P1.** Há 33 ficheiros de testes frontend. Seis usam `renderToStaticMarkup`; os restantes incluem testes de helpers e clientes. Não foi encontrada configuração Playwright neste checkout. Os 147 testes são uma base útil, mas não demonstram persistência após interação, comportamento de foco, layout em quatro resoluções ou ausência de respostas assíncronas desatualizadas.

**Ação:** E2E com API/base sintética separada, testes de componentes e regressões visuais. Cobrir particularmente geração/aceitação da semana, mudança de contexto durante pedidos, perfil, variantes e receção de compras. O `generateProposal` assíncrono atual não evidencia uma guarda de revisão de contexto em todas as respostas; tratar como risco a reproduzir antes de classificar como bug confirmado.

### A13. Autenticação e permissões continuam uma entrega própria

**Prioridade P0 antes de exposição pública.** As rotas verificam entidades e contexto familiar, mas os handlers revistos não têm dependência de identidade autenticada. A entrada por Family UUID é uma ferramenta de desenvolvimento, não um acesso de produção.

**Ação:** utilizador/contas, família, pessoa e consentimentos com autorização no servidor. Não é necessário interromper o trabalho local de UX; é necessário concluir esta fronteira antes de disponibilizar dados pessoais em produção.

### A14. Documentação histórica mistura estados antigos com capacidades recentes

**Prioridade P1 de execução.** `implementation-status.md` tem incrementos recentes no início e listas posteriores que ainda descrevem reconciliação de compras e variantes reutilizáveis como pendentes. O roadmap integrado conserva diagnósticos anteriores à implementação de presenças por slot e mapa. O quadro T01–T12 e os ADRs recentes dão melhor contexto, mas também contêm registos intermédios.

**Ação:** manter um estado canónico por capacidade, com branch/SHA e evidência. Usar histórico como histórico. Não começar trabalho pela frase mais antiga de “próxima branch”.

## 4. Decisões de UX a transportar do protótipo

- Marca **NutriFlow AI** em relevo e **Casa à Mesa** em subtítulo.
- Claro marfim com verde discreto; escuro carvão/cinza quente com âmbar, sem superfícies verdes.
- Uma ação principal por ecrã; home compacta; detalhe em painel; formulários progressivos.
- Semana como superfície operacional, avatares para presenças e porções por pessoa.
- Avaliação de gosto, nutrição, restrições e FODMAP separadas; desconhecido permanece desconhecido.
- Adaptação explica quem é afetado, o que muda e o que falta rever; aplicação explícita.
- Compras simples à primeira vista, aprofundando produto, embalagem, loja e receção.
- Barras de scroll discretas/ocultas conforme preferência aprovada, preservando scroll, foco e acesso a conteúdo. Não ocultar overflow para disfarçar problemas de layout.
- Low-fi e PDF são **ferramentas temporárias de apresentação**, nunca destinos centrais da app de produção. Devem ficar limitados ao modo de demonstração.
- O HTML único é uma entrega académica. A aplicação de produção mantém React/TypeScript, APIs, testes e ficheiros organizados; não se migra o motor demonstrativo `CasaModel`.

## 5. Percurso e arquitetura de informação propostos

**Navegação principal:** Início · Plano · Receitas · Família · Compras. Despensa acessível diretamente a partir de Compras/Receitas e como atalho lateral no desktop. Definições e integrações em acesso secundário. Não adicionar uma sexta ou sétima entrada à barra inferior.

Família contém pessoas e administração; não confunde pessoas com contas de acesso. Receita contém ingredientes, preparação, avaliações e variantes, com edição em ecrã/painel focado. Planeamento integra fontes caseiras e externas no contexto de cada refeição.

Fluxo principal: criar família → adicionar pessoas/necessidades → criar/importar receitas → organizar presenças → gerar ou editar semana → rever/adaptar → aceitar → preparar compras → receber stock → registar consumo/feedback → melhorar propostas seguintes.

Isto é uma proposta de execução alinhada com o protótipo; a aplicação atual usa Início/Plano/Compras/Pessoas/Casa. A mudança terá testes e mapeamento de todas as funções de Casa, sem as eliminar.

## 6. Sequência recomendada

1. Consolidar o baseline e os PRs empilhados, atualizar estado canónico e disponibilizar DB de teste isolada.
2. Introduzir tokens, componentes, ícones, marca, temas e política de movimento; portar a home e os avatares.
3. Migrar um percurso completo: pessoa com exclusão → jantar partilhado → variante → compras. Primeiro reutilizar APIs existentes.
4. Migrar as restantes superfícies operacionais; adicionar presenças individuais/grupos/padrões e bloqueios de decisões.
5. Completar importação NLP, avaliação ML/deep learning, consumo/sobras e fontes externas por entregas próprias.
6. Integrar saúde, adaptação de objetivos, mobile, autorização e operação de produção sem voltar a sobrecarregar a home.

Cada incremento tem uma entrega visual observável. Não se adia a nova interface até completar todos os fornecedores e funcionalidades de longo prazo.

## 7. Fontes de decisão

- [Continuidade](../development-continuity.md), [estado do domínio](../domain/implementation-status.md), [quadro T01–T12](../vision/implementation-task-board.md).
- [Roadmap integrado](../vision/integrated-family-meal-planning-roadmap.md), [roadmap de planos e orientação](../vision/nutrition-plan-guidance-roadmap.md), [prioridades centrais](../vision/core-meal-planning-priorities.md), [visão do produto](../vision/product-vision.md).
- [Arquitetura de informação atual](frontend-information-architecture.md), [arquitetura alvo](../architecture/target-architecture.md), ADR-007 e ADR-059 a ADR-072.
- Código local no checkpoint identificado e recursos do GitHub no mesmo SHA/main. Documentos anteriores de outubro são fontes históricas, não verificações efetuadas em novembro.

Nesta auditoria não foram alteradas funcionalidades, criadas migrations, executados seeds, manipulados dados familiares, feitos commits, pushes ou merges. Os novos documentos são o plano de transformação, não uma declaração de implementação concluída.
