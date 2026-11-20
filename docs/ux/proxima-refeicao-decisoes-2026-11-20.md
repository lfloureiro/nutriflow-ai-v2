# Ecrã «A nossa semana» — carta «Próxima refeição» (decisão aprovada)

Estado da decisão: **fechada pelo utilizador, 20/11/2026**. Referência visual: mockup de tema escuro aprovado na conversa, baseado no protótipo `Casa_a_Mesa_High_Fidelity.html`. Referência funcional: NutriFlow AI v2, não o motor ilustrativo do HTML.

## Contrato de produto

1. **Marca global fixa:** NutriFlow AI; subtítulo Casa à Mesa; versão proveniente de `apps/web/package.json`. Menu desktop: Início, A nossa semana, Receitas, Família, Compras, Despensa, bloco «Inteligência à mesa» e cartão da família.
2. **Carta editorial acima da grelha:** imagem/ilustração, próxima refeição em horário familiar, título, contexto e ação. A fotografia não prova composição nutricional, FODMAP nem elegibilidade.
3. **Seleção temporal:** respeitar o fuso da família; usar horas guardadas quando existe evento e horários padrão quando não existe; ignorar momentos passados e consumidos, avançando para amanhã quando necessário. Recalcular ao passar de horário e ao mudar o dia.
4. **Refeição já definida:** apresentar a entrada guardada e abrir o detalhe da refeição, sem emitir uma recomendação alternativa.
5. **Momento sem refeição guardada:** usar o motor de propostas `POST /api/families/{family}/weekly-planning/proposals` para **um único slot**, baseado em candidatos reais do bootstrap de planeamento. Reutilizar verificações por pessoa, restrições obrigatórias, evidência nutricional e preferências disponíveis no motor existente.
6. **Sem aplicação automática:** exibir proposta como *por confirmar* e encaminhá-la para o mesmo drawer de revisão, adaptações e confirmação da semana. «Outra sugestão» exclui o candidato anterior do catálogo usado na nova consulta. Erros, zero candidatos e dados incompletos não se tornam sucessos fictícios.
7. **Presenças:** neste primeiro incremento, quando não existem presenças explícitas do horário no contexto recebido, a consulta considera as pessoas registadas na família e exige revisão. Nunca se afirma que todas vão participar; exige verificação adicional com a agenda de presenças. A geração automática de refeição familiar requer pelo menos duas pessoas.
8. **Continuidade do plano:** a carta consulta o próximo dia e o seguinte independentemente da semana que está a ser navegada; o conteúdo histórico do mapa e dos dados guardados não é modificado. O frontend nunca calcula o score nutricional.

## Implementação iniciada — v2.0.69

- `nextMealHero.ts`: determinação do próximo horário a partir dos registos reais, independente do fuso do browser.
- `NextMealHero.tsx`: carta, carregamento somente leitura, aplicação do motor familiar e tratamento explícito de erro/sem proposta.
- `nextMealHero.test.ts`: fusos, transição ao dia seguinte, refeição existente e concluída.
- `FamilyMeals.tsx`: carta no ecrã semanal e navegação para detalhe/edição.
- `WeeklyProposalPreview.tsx`: aceita proposta externa de um slot **apenas para revisão**, sem persistência automática.
- `next-meal-hero.css`: apresentação responsiva conforme mockup aprovado; tema claro/escuro.
- `verifiedRecipePhoto`: catálogo inicial de fotografias ilustrativas CC0, por nome exato e com link para fonte; imagens não devem ser procuradas em tempo real por substring arbitrária.

## Política e inventário de imagens

As receitas da API não possuem, neste ponto, um campo autoritativo de fotografia. Não fazer escrita em DB real para adicionar imagens; usar apresentação com catálogo curado no frontend enquanto se prepara um modelo versionado de `recipe_image` (identidade da receita, URI, fonte, autor, licença, data de verificação, tipo *ilustração/foto do prato*, estado de revisão e fallback).

Catálogo externo inicial, consultado na Wikimedia Commons (CC0 1.0; fotografias ilustrativas, **não** imagens comprovadas das receitas da família):

| Nomes com correspondência explícita | Ficheiro Commons |
| --- | --- |
| Salmão no forno com ervas; Salmão no forno com ervinhas da provença | `Steckenroth, salmon on baked vegetables.jpg` |
| Pão, queijo e tomate; Torrada com queijo | `Toast with cheddar cheese and tomato.jpg` |
| Frango rápido | `Chicken plate.jpg` |
| Omelete de espinafres | `An omelette.jpg` |

Cada ficheiro conserva ligação à página original e é indicado como *fotografia ilustrativa*. Receitas sem correspondência exata têm a imagem local `/images/shared-meal.svg`, não fotografia inventada. **Não está concluída a cobertura fotográfica de todas as receitas.** O passo seguinte será auditar o catálogo real de receitas e curar fotografias adequadas, de preferência através de um campo de imagem por receita com moderação humana.

## Gates ainda obrigatórios

- Web CI: TypeScript, Vitest e build.
- API CI e UX E2E sintético no **mesmo SHA**.
- Teste sintético da chamada de proposta de um slot e de entrada no drawer; cobertura de presenças/exclusões antes de afirmar personalização completa.
- Auditoria visual 1440/1024/768/390 e zoom 200%, temas claro/escuro, i18n e acessibilidade de foco/fecho.
- Teste de disponibilidade das URLs externas, licenças e adequação visual de cada fotografia.
- Manter PR #76 draft; `main`, API principal, dados familiares reais e serviços locais intactos. Não declarar v2.1.0 pronta só com esta implementação.

## v2.0.70 — apresentação do ecrã semanal aprovada (20/11/2026)

- A carta dinâmica da v2.0.69 é colocada no topo visual do ecrã semanal. Não se repete o título longo do editor; as restantes vistas e ferramentas mantêm-se acessíveis num disclosure «Outras vistas e ferramentas de planeamento», sem eliminar capacidades.
- A sidebar recupera o cartão «Inteligência à mesa · Interpretar. Aprender. Explicar.» do protótipo. Ao ativá-lo, abre a vista de recomendação já existente. Bloco oculto no menu móvel para não competir com os cinco destinos.
- Os controlos de semana anterior/atual/seguinte continuam disponíveis abaixo da carta. Todos os dados e refeições guardados conservam-se inalterados.
- **Pendências:** testar fluxo com API sintética e avaliar se o motor de um slot incorpora suficientemente o histórico/variedade semanal; rever presenças antes de aceitar, confirmar licenças de fotografias e completar cobertura de imagens; CI três gates no SHA final; comparar screenshots reais e zoom 200%. PR #76 draft, sem alteração de base real.

## Correção Windows — 20/11/2026 — colisão de nomes `NextMealHero`

- **Incidente reproduzido pelo utilizador:** ecrã branco e `npm run build` com TS1192, TS2305, TS1261, TS1149, TS7006. Causa: `NextMealHero.tsx` e `nextMealHero.ts` diferiam só em maiúsculas/minúsculas; no Windows/NTFS, os dois caminhos colidem, embora o CI Linux aceite ambos.
- **Correção:** o componente passa a `NextMealBanner.tsx`; a lógica de seleção/calendário passa a `nextMealSelection.ts`. Importações corrigidas em `FamilyMeals.tsx`, `WeeklyProposalPreview.tsx`, `nextMealHero.test.ts`; ficheiros com nomes antigos eliminados do Git.
- O CI Linux anterior não detetava colisões de nomes por case. Adicionar verificação de caminhos únicos sem distinção entre maiúsculas/minúsculas à rotina de qualidade do repositório, para evitar regressões.
- **Recuperação local segura:** confirmar `git status --short`, branch esperada e `git fetch`; atualizar só se árvore limpa. Depois confirmar que não sobram ficheiros com nomes antigos e executar `npm run build`. Vite 5173 não deve ser duplicado; API/DB intactas.
- Não interpretar 3/3 CI como substituição de validação Windows e de navegador. O ecrã branco não foi causado pelo motor nutricional nem pelos dados familiares.

## v2.0.71 — página «A nossa semana» aprovada, sem ruído extra (20/11/2026)

**Decisão visual explícita a partir das duas capturas anotadas pelo utilizador.** A semana tem só três blocos visuais: (1) carta «Próxima refeição» dinâmica, (2) navegação entre semanas e (3) grelha de 7 dias × 4 refeições. Remove-se a faixa de alerta geral assinalada com **1 X** e retiram-se completamente desta página o disclosure e os separadores «Planear próxima semana», «Hoje», «Semana», «Recomendar» assinalados com **2 X**. O dia mantém-se no Início; a recomendação dedicada pode ser aberta pelo bloco «Inteligência à mesa» do menu. Os modos e respetivos motores continuam implementados e sem mudanças de API; só deixa de haver menu de modos dentro da semana.

**Reconstrução visual da grelha:** `WeeklyProposalPreview.tsx` introduz `simpleWeekView` para proteger fluxos de planeamento que reutilizam o componente. No modo simples, não há `WeekOverview` nem botão geral de gerar proposta acima da grelha; o botão de confirmar proposta selecionada pode continuar acessível. `ux-planning.css` fixa, em desktop acima de 1100 px, 90 px de coluna com ícones por refeição, 7 colunas de dias, 56 px de cabeçalho, linhas de cartões compactos de 134 px; os dias mostram número grande (sem mês) e abreviatura, o dia ativo mantém destaque. Cartões vazios têm `+` e «Adicionar» centrados e tracejado; refeições planeadas têm fundo neutro e um único badge; propostas que exigem revisão têm cartão em tom quente e badge «Por verificar»/«Adaptar», sem duplicação de indicadores. Os cartões mantêm dados reais, acessibilidade e drawers. Em ecrãs abaixo de 1101 px mantém-se a escolha de dia com cartões 2 colunas; abaixo de 580 px há uma coluna. Estilos limitados a `nf-week-map-final` para não alterar outros modos.

**Restrições:** não alterar receita, nutricionismo, FODMAP, consentimento, algoritmo, API, DB, `main`, serviços locais. A foto da carta continua apenas ilustrativa, com origem declarada. A vista precisa de comparação visual real em 1440/1024/768/390 e zoom 200%, bem como testes Web/API/UX E2E no mesmo SHA. PR #76 mantém-se draft; marco de revisão manual v2.1.0.
