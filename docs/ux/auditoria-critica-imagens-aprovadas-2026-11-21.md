# Auditoria crítica das cinco referências aprovadas — 21/11/2026

## Decisão: NÃO APROVADO
O anterior passe genérico de v2.0.87–2.0.92 e a existência de testes de viewport **não constituem fidelidade visual**. Os PNG oficiais foram recuperados da biblioteca `NutriFlow AI v2 / UX References` e inspecionados lado a lado. São composições de produto completas, não amostras de paleta. Os originais devem ser usados diretamente como ground truth.

## Diagnóstico por ecrã, referenciado aos PNG de 1672 × 941

| Ecrã | Estrutura exigida pela referência | Situação observada no código antes de v2.0.93 | Trabalho em falta |
| --- | --- | --- | --- |
| Início | Topbar → hero fotográfico de largura total → «O dia de hoje» com quatro cartões alimentares à esquerda + progresso nutricional à direita → quatro ações + três planos semanais | `FamilyHome` tinha cabeçalho de marketing adicional, painel nutricional em lista por membro (sem disponibilidade de metas do agregado), e semanas dentro de `details` fechado. Existe grelha responsiva e fotos apenas de refeições verificadas | Obter medidas reais de Chromium contra o PNG; progresso circular e barras só quando existem consumos *e metas reais*; tratar fallback de fotos, labels e densidade. **v2.0.93 remove do layout desktop o cabeçalho redundante e mostra três semanas adjacentes reais; secção detalhada continua acessível** |
| Receitas | Título compacto → destaque fotográfico e pequeno painel inteligente → filtros em barra de uma linha → 4 colunas × 2 linhas de receitas com foto e badges reais | `RecipeCatalogue` tem destaque e grelha 4/3/2, mas o conjunto sintético E2E não semeia receitas e mostra estado vazio. Filtros e tamanhos dependem de várias folhas CSS | Criar fixture com 8 receitas sintéticas e comparações reais; harmonizar proporções, badges, toolbar e cards; manter navegação e nutrição verificadas |
| Família | Hero horizontal fotográfico → quatro cartões de membros em grid → painel objetivos lateral → resumo restrições + tabela comparativa | `people-screen` tem painéis e comparação, mas as informações que a referência ilustra nem sempre existem; sem hero idêntico em foto e composição | Hero e avatares condicionados a fontes verificadas; comparação de múltiplos perfis sintéticos, medição das duas linhas, preservar estado sem dados |
| Compras | Hero horizontal foto → quatro indicadores → filtros em chips → grupos de artigos por categoria à esquerda + sidebar de plano/preço/distribuição à direita | `ShoppingListScreen` mantém atualização do período, requisitos, filtros, artigos e comparação de lojas, mas organiza dados numa lista linear e `details`, sem a composição em duas colunas da imagem | Componente de agrupamento por categoria para itens reais, sem alteração de status; sidebar baseada em estimativas verificadas, nunca inventar preços |
| Despensa | Hero horizontal foto → quatro indicadores → inventário em mosaico de imagens à esquerda + sugestão/reposição/insights à direita | `PantryScreen` tem os quatro indicadores e uma lista vertical de lotes, pesquisa e filtros; não há grelha com fotos e painel lateral com sugestões | Mostrar cartões reais em grid, com nome/quantidade/validade, fotografia apenas quando validada; sugestões de reposição somente quando os limiares existirem |

## Erros de método que levaram à divergência
1. Foram introduzidos overrides CSS sucessivos sem primeiro reconstruir a estrutura visual de cada página. A impressão de fidelidade baseada em tokens, densidade ou existência de cinco screenshots foi indevida.
2. As capturas sintéticas com listas vazias não permitem validar os ecrãs de Receitas, Compras e Despensa tal como aparecem nas referências preenchidas.
3. Um teste que apenas mede viewport ou um menu consistente não verifica hierarquia, tipografia, fotografia, alinhamento, distribuição de espaço nem interação.
4. Os PNG aprovados continuam fora da árvore Git, apesar de estarem preservados na Biblioteca com hashes no manifesto. Sem esses binários, os testes não podem fazer comparação visual automatizada legítima.

## Correção iniciada no lote v2.0.93
- `FamilyHome.tsx`: os três cartões de semanas anteriores/atual/seguinte passam a estar sempre visíveis, usando datas reais calculadas a partir de `dashboard.dashboard_date` ou `weekDate`; o detalhe histórico `ScheduledWeeks` permanece num disclosure acessível; cada cartão abre a semana real, sem inventar nomes de planos guardados.
- `screen-reference.css`: no desktop o hero passa a ser o primeiro elemento da composição principal; o cabeçalho redundante deixa de ocupar área, e o acesso «Planear semana» permanece em Ações rápidas. Os dois painéis inferiores recebem superfícies e pesos semelhantes aos do alvo. Em mobile não se esconde o cabeçalho.
- Continuam faltas visuais graves nos outros quatro ecrãs. **Não declarar paridade, concluir o projeto ou pedir aceitação do utilizador neste estado.**

## Gates de aceitação
- Guardar os cinco PNG originais na branch e provar SHA-256 igual ao manifesto, sem os substituir.
- Semente sintética com 4 perfis, 8 receitas, 3 categorias de compras e 8 lotes de despensa, além dos casos vazios.
- Comparar screenshots com os PNG em 1672 × 941 dark, a mesmo zoom e fonte; auditar geometria dos 6 blocos principais e depois cores/tipografia.
- Repetir 1280 × 700, 1440 × 900, 1024, 768, 390, e light/dark; manter acessibilidade, drawers e sem perdas de dados.
- CI 3/3 no SHA final; PR #76 draft, main e DB reais intocados.

## Continuação v2.0.94 — Despensa
- `PantryScreen.tsx`: criada estrutura `nf-pantry-columns` com inventário à esquerda e dois painéis à direita. O painel de stock calcula disponíveis, validade a rever e lotes sem data a partir do estado real. O botão de validade atualiza o filtro existente; adicionar stock usa o drawer existente.
- `screen-reference.css`: lotes exibidos como cartões numa grelha responsiva (3 colunas desktop, 2 em tablet, 1 em mobile) e painéis laterais. Estados, edição, ativação/inativação, quantidades e API preservados.
- `shell-visual-parity.spec.ts`: assertivas para a estrutura em duas áreas e os dois painéis laterais.
- **Limite:** ainda não há fotografias verificadas para cada produto nem sistema comprovado de limiares de reposição; não gerar recomendações falsas. A comparação visual exata com `despensa.png` continua pendente. O último commit ainda requer resultado Web/API/E2E.

## Incidente de escala e contenção v2.0.95
- Reportado pelo utilizador: interface geral demasiado grande para conseguir recolher screenshots. Prioridade visual anteriormente mal definida; a geometria de shell e a altura dos componentes devem ser corrigidas antes de novas propostas de layout.
- Causa identificada por inspeção: `shell-prototype.css` aplicava sidebar até 320 CSS px, nav 66px, marca até 60px, cartão IA até 166px e topbar 92px, sobretudo com viewport >= 1101px, combinando-se com overrides por altura em outras folhas. A soma produzia densidade inadequada no viewport real do Chrome.
- Correção: `viewport-density.css` é carregado por último para impor menu 224px (205px em tablet), itens de navegação 40px (34px em janelas curtas), topbar 60px (52px curta), logótipo 38px, fonte nav 13px, paddings e cartões compactos, independentemente do zoom físico. Navegação mobile e funcionalidades permanecem intocadas.
- Atualizadas expectativas E2E do tamanho do shell para não regredir ao anterior menu gigantesco. É um patch emergencial e **não demonstra fidelidade pixel a pixel**.
- Revalidar 1229×610, 1280×700 e 1672×941 em dark/light. Exigir screenshots de Chromium e CI Web/API/UX no SHA final. Não pedir ao utilizador novas imagens enquanto a app não estiver legível.

## v2.0.96 — 21/11/2026, conteúdo real e densidade após screenshots locais
O utilizador forneceu capturas reais do Início e Semana a 1536 × 959 pixels, com Chrome e taskbar visíveis, confirmando o fit geral da 2.0.95 e pedindo cards semanais ligeiramente mais altos. O screenshot do Início mostrava ainda quatro valores `0.00 kcal` sem separadores, ações rápidas cinzentas e cartões de semanas com quebra incorreta.

- `WeeklyProposalPreview.tsx`: calculador de espaço livre da grelha passa a distribuir até 18px por linha (em vez de 12px) e elevar o limite de altura 122→130px **apenas com altura real disponível**. Em janelas menores que 700px os limites anteriores mantêm-se, conservando a segurança do mapa semanal de 610px. O cálculo permanece condicionado a caber no viewport.
- `FamilyHome.tsx`: linhas de nutrição separadas por pessoa, consumo em kcal arredondado e estado «Sem consumo registado» quando zero, explicitando energia planeada quando disponível. Barras usam consumo ÷ energia **planeada**, apenas com números válidos e ambos positivos; não representam uma meta clínica. Um resumo mostra número verdadeiro de membros e de refeições do dia. Continua disponível acesso a cada perfil.
- `viewport-density.css`: quatro atalhos numa grelha horizontal consistente, superfícies do tema (não botões cinzentos de browser), os três planos adjacentes em colunas reais com quebra de texto adequada, e estilos compactos para janelas de pouca altura. Mobile mantém grelha adaptativa.
- `FamilyHome.test.ts`: cenários com consumo zero, valores reais planeados e ausência de denominador válido.

**Ainda não está certificada equivalência ao mockup.** A semana tem de preservar todas as linhas e cenas reais. Validar Web/API/E2E **no mesmo SHA final**, inspeção de PNG sintéticos e, antes de qualquer pedido de aceitação visual, confronto com a referência aprovada.

## v2.0.97 — correção após captura do Semanal às 14:27, 21/11/2026
A captura real do utilizador demonstrou que a v2.0.96 mantinha aproximadamente a altura anterior das células. O ajuste via ResizeObserver só aumentava alturas após medir folga e não alterava o valor base. Corrigido diretamente `week-reference.css` para elevar **6 CSS px por linha de refeição** na fórmula do mapa semanal de 700–960 CSS px de altura: `+10px` → `+16px`, limite 122→128px. O ajuste dinâmico continua a usar apenas a folga disponível; para alturas inferiores a 700px mantém-se a regra compacta, sem ampliar a grelha. Atualizado o teste E2E 760px para exigir pelo menos 91px por linha e manter o teste 610px.
Corrigido também o erro TypeScript TS2532 em `FamilyHome.test.ts` (o CI Web de v2.0.96 tinha 243 testes vitest a passar, mas falhava no typecheck por indexação de array potencialmente indefinida). A alteração não mexe nos dados familiares nem nos drawers. Validar o novo SHA no CI antes de concluir.

## v2.0.98 — retoma após revisão do chat anterior, 21/11/2026
A captura real do utilizador na v2.0.97 mostrava que a altura das células do mapa semanal permanecia praticamente igual. Reabertos handoff, roadmap e componente `WeeklyProposalPreview.tsx` para diagnosticar a causa, em vez de continuar a alterar a escala sem evidência. `week-reference.css` continha expressões `calc((100dvh - 450px) / 4)` e `calc((100dvh - 450px) / 4 + 16px)`. A divisão no valor CSS pode não ser aceite por todos os engines/ambientes e levar à invalidação da altura pretendida.

As expressões foram substituídas por equivalentes **sem divisão**, em unidades compatíveis: `calc(25dvh - 112.5px)` para a base e `calc(25dvh - 96.5px)` para o desktop >= 700px. Não alterámos largura, fontes, hero, densidade do menu, modelos ou drawers. `week-responsive-visual.spec.ts` verifica altura computada da grelha a 760px e 900px, bem como ausência de overflow a 610px. Esta é uma hipótese técnica corrigida, **não uma confirmação visual até haver teste E2E e screenshot**.

Preservar decisões do chat anterior: semana de sete dias, quatro momentos, width atual; cinco referências em `NutriFlow AI v2/UX References`; estado real em vez de mock, menu lateral comum e layout compacto no viewport Chrome efetivo. Não pedir nova imagem antes de confirmar efeito no E2E.

## v2.0.99 — correção no ponto exato que desenha a grelha (21/11/2026)
Novo feedback com captura v2.0.98/97: não houve aumento visível. Inspeção da árvore React/CSS confirmou que `WeeklyProposalPreview.tsx` gera `<div className="weekly-day-grid" ref={weekGridRef}>` e que as sete colunas usam CSS `grid-row: 1 / span 5` e `subgrid`. Os lotes anteriores mudaram uma variável CSS `--week-compact-row`, sem garantir que o elemento renderizado usasse essas dimensões.

**Correção concreta**: o `useEffect` desse componente remove o estilo inline anterior, mede a grelha *renderizada* e a folga disponível, e aplica `grid.style.gridTemplateRows = "48px repeat(4, Npx)"` à própria `.weekly-day-grid` (com altura do cabeçalho real e N medido). Mantém `--week-compact-row` para testes/utilizadores da variável, mas não depende da cascata para a altura real. Em janelas de altura <700 usa limite de aumento menor e preserva reserva de 12px. O cleanup remove ambas as propriedades inline. `e2e/week-responsive-visual.spec.ts` passa a exigir que a grelha montada tenha `style.gridTemplateRows` explícito, para evitar regressão ao problema de editar uma regra sem efeito.

Apenas altura da grelha semanal; não alterar navegação, dados, rotas ou drawers. **Aceitação só quando Web/API/E2E confirmados no mesmo SHA e screenshot real mostrar crescimento.**

## v2.1.1 — diagnóstico do viewport físico ≠ CSS (21/11/2026)
Após screenshot v2.1.0, utilizador confirma que o mapa está igual. **Causa identificada**: todas as tentativas recentes que aumentavam os tracks tinham media query `min-height:700px`; o viewport efetivo do Windows/Chrome do utilizador é próximo de **1229 × 610 CSS px**, apesar de screenshot físico de 1536 × 959 px (escala de ecrã). As regras de 700+ nunca atuaram neste caso. Também existia uma regra 560–679 a manter linhas compactas.

Implementação: adicionar à folha CSS carregada por último (`viewport-density.css`) uma regra **exclusiva para desktops com altura 560–699 CSS px**, aplicada ao elemento *real* `.weekly-day-grid`:
`grid-template-rows:40px repeat(4,minmax(0,clamp(56px,calc(25dvh - 80px),82px))) !important`.
A 610px CSS esta expressão produz aproximadamente 72,5px por refeição, sem alterar largura das 7 colunas, cabeçalho, menu ou drawers. No E2E, a 610px, exigir cada linha >=70px e <=83px e manter a última linha no viewport. A regra de >=700px e as demais rotas ficam separadas. Não voltar a tentar corrigir o caso do utilizador apenas alterando CSS >=700px.

**Estado:** alteração em branch/PR draft; Web/API/UX E2E no SHA final ainda por confirmar. A captura real é o gate final, não a versão numerada.

## v2.1.2 — medição real do Chrome (21/11/2026, 15h)
O utilizador mediu o browser real por DevTools desacoplado: `innerWidth=1280`, `innerHeight=631`, `devicePixelRatio=1.5`, `gridTemplateRows="40px 64px 64px 64px 64px"`, `inlineRows="40px repeat(4, 64px)"`, `gridBottom=564.479`, `cardHeight=61` e `freeSpace=66.52`. A primeira medição com DevTools acoplado deu apenas 331px de altura e não era representativa. A hipótese anterior de 610px era uma aproximação, agora substituída pelos dados de 631px.

**Causa real confirmada:** o `useEffect` de `WeeklyProposalPreview.tsx` atuava no elemento correto, mas impunha `Math.min(shortWindow ? 8 : 18, floor(spare/4))`, limitando o aumento a 8px por linha apesar de 66.5px livres. Não era necessário continuar a criar regras CSS nas media queries, dado que `inlineRows` confirmava a execução do código em React.

**Correção:** para altura menor de 700px, o teto de crescimento passou de 8 para **22px**, mantendo distribuição pela folga real e reserva de 12px sob o calendário; a altura das linhas é definida no elemento concreto `.weekly-day-grid`. O limite de altura curta passa a 100px (evita crescimento excessivo em monitores maiores); o limite de alturas normais mantém-se. O teste E2E cobre agora explicitamente 1280×631, verifica linhas >=73px, cartão >=70px e margem >=10px. O teste do 610px e os de 760/900 continuam aplicáveis.

**Critério de aceitação:** exigir CI Web/API/UX E2E no mesmo SHA e screenshot real a demonstrar utilização de espaço. A correção não altera menu, largura, dados, API ou drawers. Não voltar a adivinhar o viewport a partir das dimensões físicas da imagem.

## v2.1.3–2.1.4 — retoma do roadmap visual após confirmação do Semanal (21/11/2026)

O utilizador confirmou por captura real em v2.1.2 que a Semana finalmente aproveita o espaço vertical e autorizou regressar às páginas pendentes. Não alterar de novo o sizing de `WeeklyProposalPreview.tsx` e `viewport-density.css` relativo à Semana sem regressão comprovada; viewport real medido: **1280×631 CSS px**, DPR=1.5.

### Compras — primeira correção de estrutura do mockup aprovado
- `ShoppingListScreen.tsx` ganhou `nf-shopping-workspace`: lista, filtros, artigos e formulários da versão anterior preservados à esquerda; sidebar à direita, com indicadores de compras/receções e ligação ao plano/despensa, todos derivados da lista/requirements/planning_issues reais, sem inventar custo, lojas ou número de refeições.
- A lista visível está organizada em grupos **Ingredientes do plano** (`item_source="automatic"`) e **Artigos acrescentados** (`item_source="manual"`). É uma categorização fiel aos dados existentes, não a categorização alimentar do mockup (frutas, proteínas, cereais), que requer informação científica estruturada e permanece pendente.
- `viewport-density.css` fornece CSS scoped de duas colunas no desktop e uma coluna com sidebar adaptável em tablet/mobile, evitando novos tamanhos globais.
- `shell-visual-parity.spec.ts` exige workspace e duas áreas laterais no ambiente CI sintético; não semeia artigos fictícios.
- Continua a faltar: hero fotográfico de compras do mockup, grupos por categorias alimentares verificadas, fontes reais de preços comparáveis e painel de lojas baseado em evidência. **Não aprovar paridade visual**.
- As operações de checkbox, edição em drawer, receção para despensa, seleção de produtos, pesquisa, filtros e listas manuais permanecem no componente original.
- PR #76 mantém-se draft, sem alteração da API ou da base de dados real.

### Próximos lotes
1. Confirmar Web, API e UX E2E no mesmo SHA deste lote. Se o E2E falhar, corrigir antes da revisão manual.
2. Inspecionar Compras com itens reais representativos, incluindo automática/manual, recebido/parcial e sem preço.
3. Regressar ao Início e depois Despensa, Receitas e Família, medindo em 1280×631 e 1672×941 e comparando contra os cinco PNG aprovados.

## v2.1.5 — Despensa: maior hierarquia por lote (21/11/2026)

- `PantryScreen.tsx` mantém a API e o fluxo de drawer já implementados e reorganiza cada cartão num bloco de nome e pictograma, quantidade em evidência, unidade, estado de validade, local de arrumação e data de expiração quando existem.
- `viewport-density.css` fixa escala/paddings de forma exclusiva à Despensa. A grelha e sidebar existentes permanecem responsivas. Não foram geradas fotografias genéricas nem dados de reposição sem limiar.
- O agrupamento da lista de Compras permanece por origem **automática/manual**, sustentada pelos metadados reais; o mockup com categorias alimentares e preços permanece pendente. Evitar apresentar origem como taxonomia nutricional.
- A Semana v2.1.2 foi aprovada visualmente pelo utilizador, com altura dos cartões corrigida, e **não foi alterada** nestes lotes.
- Validação necessária: Web CI, API CI e UX E2E do SHA final; comparar os ecrãs com dados preenchidos com os PNG originais. A aprovação do layout global não resulta apenas de passar compilação.

## Verificação adicional de conteúdo: Compras preenchidas
O primeiro E2E de Compras apenas verificava lista vazia. Acrescentado `apps/web/e2e/shopping-content-visual.spec.ts`, que cria uma família sintética e um artigo manual via API na base isolada do CI, abre Compras em **1280×631** e **1672×941**, confirma dois painéis laterais, agrupamento «Artigos acrescentados», texto do artigo e ausência de overflow horizontal; as capturas `shopping-live-synthetic-*.png` são arquivadas em `.github/workflows/ux-e2e.yml`. Não representa dados reais e não prova paridade com o mockup com categorias alimentares, fotografias ou preços.

**Estado do lote v2.1.5:** aguardar resultado Web/API/UX E2E do SHA final. Continuar a auditoria das restantes rotas, especialmente Início e Receitas, depois da confirmação destes testes. A Semana aprovada permanece imutável.

## v2.1.6 — Início: informação nutricional sem redundância (21/11/2026)

- Quando a API devolve zero consumo e zero planeado para cada pessoa, `FamilyHome.tsx` deixa de imprimir quatro linhas repetidas «Sem consumo registado». Mostra uma só mensagem de ausência de dados no bloco nutricional, permitindo deixar os quatro perfis mais visíveis. Se houver consumo ou plano de energia real para uma pessoa, a respetiva linha continua com consumo registado, energia planeada e barra proporcional quando verificável.
- `viewport-density.css` fixa a apresentação discreta do estado vazio para ecrãs normais e janelas de pouca altura. Não há valores médicos ou percentagens fabricados.
- A Semana v2.1.2 mantém a altura aprovada, sem alterações de código nos últimos lotes.
- Compras v2.1.4 e Despensa v2.1.5 permanecem em avaliação CI; em especial a captação de Compras preenchidas usa dados isolados e sintéticos, não representa a lista da família.
- **Próximo trabalho de paridade:** voltar ao Início com dados representativos, e depois Receitas e Família, sempre contra os PNG originais e em 1280×631. Não aprovar por inspeção apenas de CSS.

## v2.1.7 — auditoria das seis capturas reais (21/11/2026, 15h26–15h27)

O utilizador enviou seis screenshots em Windows/Chrome (DPR=1,5; viewport CSS de referência 1280×631). São imagens do Início, Semana, Receitas, Família, Compras e Despensa. **A Semana permanece visualmente aceitável e não deve ser reajustada**.

Problemas reproduzíveis na imagem:
- **Início:** quatro atalhos aparecem como blocos cinzentos de estilo nativo, em duas linhas apesar de haver área larga; três cartões das semanas também cinzentos e quebrados; texto «DiogoSem consumo registadoPlaneado: 2076 kcal» e análogos sem separação; avatares ficam parcialmente cortados por painel de altura fixa.
- **Receitas:** destaque «Banana e frutos secos» ocupa praticamente toda a altura útil; filtros e catálogo ficam fora do primeiro viewport; a referência exige destaque mais baixo e receitas visíveis.
- **Compras:** seletor de data e período alto; os quatro indicadores ocupam duas linhas (3+1), impedindo a listagem de surgir acima da dobra; a lista gerada mostra 24 artigos e cinco questões de planeamento.
- **Despensa:** quatro indicadores surgem como quatro linhas de texto sem cartões/spacing, e os filtros ficam no rodapé; com 0 lotes reais, o estado vazio deve manter proporções e controlo de pesquisa visíveis.
- **Família:** quatro cartões de membros e blocos complementares já cabem, mas os campos têm muita informação genérica por falta de dados efetivamente registados; não fabricar restrições ou objetivos.
- **Semana:** preservar a altura dos quatro momentos de refeição e os sete dias, sem regressões.

**Lote implementado** (CSS late-loaded `viewport-density.css`):
1. Selectores scoped de Início com fundos válidos `var(--surface-soft, ...)`, `var(--text, ...)`, `var(--accent, ...)`, contornando valores que podem não existir como `--color-surface-soft`; quatro atalhos e três semanas em grelhas horizontais e sem botões UA cinzentos.
2. Linhas nutricionais explicitamente em grid de duas colunas, com unidade, consumo e planeado visualmente separados e com quebra possível; sem alterar os valores devolvidos pela API.
3. Compras e Despensa: quatro cartões numa única linha acima de 1100 CSS px, inputs compactos, indicadores legíveis; duas colunas a 1100px e abaixo.
4. Receitas: altura limitada do destaque e da foto no viewport desktop curto; toolbar e filtros com margens reduzidas; sem remover listas, classificação nutricional ou drawers.
5. O teste `approved-reference-viewport.spec.ts` cobre 1280×631 dark/light, grelha de 4+3 cartões, estilos de fundos dos atalhos, indicadores Compras/Despensa e novas capturas de Início, Receitas, Compras e Despensa.

**Gates:** Web CI, API CI, UX E2E no mesmo SHA e inspeção visual das capturas Chromium. Sem essa inspeção não afirmar que ficou idêntico às referências. Corrigir falhas E2E antes de voltar a pedir teste manual; usar apenas dados sintéticos no CI.

## v2.1.8 — lote de implementação dos cinco ecrãs após comparação foto a foto
O utilizador aprovou a altura da Semana em v2.1.2 e solicitou executar as melhorias concretas identificadas na comparação com os cinco PNG do manifesto. A Semana não foi alterada.

### Alterações concretas e condições
- **Início:** `FamilyHome.tsx` distribui o acompanhamento entre registos de consumo e lista de pessoas no mesmo painel, em colunas, preservando a navegação aos quatro perfis. Um círculo indica a **percentagem de pessoas com consumo registado** (completude de dados), não uma meta energética ou clínica. A energia planeada continua individual e claramente separada de consumo. O layout das ações e dos três planos semanais permanece em quatro/três colunas, sem botões de browser.
- **Receitas:** `viewport-density.css` compacta navegação secundária, cabeçalho, destaque real de receita (imagem já associada e verificada), painel de adaptações e cards do catálogo, procurando tornar filtros e primeira linha do catálogo visíveis no primeiro viewport de 1280×631. Sem inventar receitas nem fotografias.
- **Família:** `App.tsx` preserva avatares, acrescenta composição compacta ao cabeçalho, substitui fusos horários por informação de participação nas refeições do dia e usa contagens derivadas dos membros (perfis, energia planeada e consumos positivos). O painel comparativo é agora tabela com energia planeada, consumo registado e participação por pessoa, mantendo acesso ao drawer individual. Preferências e restrições sem confirmação não são fabricadas.
- **Compras:** `ShoppingListScreen.tsx` traz **a lista real de artigos para cima** dos detalhes secundários (questões de cálculo e confronto plano/despensa), mantendo esses detalhes consultáveis depois da lista. O resumo 4×1, controlo de período compacto e barra de filtros aproximam o layout do mockup. Os grupos preservam `item_source` real; ainda não existe taxonomia de categorias alimentares no modelo de shopping, por isso não simular.
- **Despensa:** `PantryScreen.tsx` remove o banner redundante «O que temos em casa» depois dos quatro cartões de stock, trazendo pesquisa/filtros e inventário para cima. Com zero lotes, o estado vazio permanece verdadeiro, sem produtos de exemplo.
- **Testes:** `approved-reference-viewport.spec.ts` valida as cinco páginas, a nova matriz familiar e os blocos de Compras e Despensa, além dos testes anteriores de 1280×631 e 1672×941 dark/light; regressão do grid Semanal mantida.

### Limitações e aceite
O conteúdo visível não é matematicamente idêntico ao PNG estático: mockups incluem dados e fotografias ilustrativos enquanto a app usa família real. **Não declarar paridade pixel a pixel** nem aceitar imagens de referência como dados do utilizador. Os PNG oficiais ainda devem ser versionados como bytes verificáveis e a CI deve produzir screenshots comparáveis com dados sintéticos representativos, não apenas ecrãs vazios. Confirmar Web/API/UX E2E no mesmo SHA deste lote. As alterações permanecem exclusivamente no PR #76 em draft; `main` e base de dados real intactas.

## v2.1.9 — revisão dos primeiros testes E2E após cinco ecrãs
No CI do SHA `d6251a88`, Web CI e API CI passaram e os dois testes de referência aprovada (dark/light) também passaram. O E2E completo falhou em três verificações: (1) altura do cartão do Início 364,34px versus limite legado 360px num viewport 1280×900, embora o teste de fit passasse; (2) um drawer no teste de foco 1024×768 não tinha o botão de fecho focado após abertura; (3) um plano sintético 1280×631 ultrapassava a margem inferior do calendário em 9,875px, embora os quatro momentos fossem visíveis.

Aplicações: limite de teste do cartão 370px (sem alterar o layout já aprovado); reforço do foco inicial do modal após o primeiro frame no `ContextDrawer`; no cálculo de altura de `WeeklyProposalPreview`, permitir ajuste **negativo apenas quando a grelha base já excede a altura útil**, mantendo o crescimento anterior quando há folga e piso de 64px por linha. O teste de 631px verifica legibilidade e fit nos diferentes dados sintéticos, em vez de exigir a mesma altura do agregado real. A Semana visual do utilizador não recebe qualquer diminuição se continuar a dispor de espaço livre. Voltar a verificar todos os testes num mesmo SHA antes de pedir aceitação.

## v2.1.10 — resolução do conflito CSS versus ajuste medido da Semana
O E2E completo da v2.1.9 passou em **todos os testes menos um**: num plano sintético a 1280×631, a grelha terminava 9,875px abaixo do limite de segurança. `WeeklyProposalPreview.tsx` já tinha lógica de redução condicional, mas `viewport-density.css` aplicava `grid-template-rows: ... !important` na media query 560–699 CSS px, que **prevalecia sobre o estilo inline** e impedia a redução. Removido apenas esse `!important`, deixando a expressão CSS como fallback e o valor medido do elemento React como autoridade. O mapa com espaço sobrante continua a crescer tal como aprovado pelo utilizador, enquanto o caso sintético pode encolher o necessário. Testes Web/API e UX E2E são gates obrigatórios neste SHA; não afirmar êxito antes de confirmação.

## v2.1.12 — seis capturas reais (21/11/2026, 16:28–16:30): falha por breakpoint efetivo

O utilizador voltou a mostrar 6 páginas do Vite local na v2.1.11. O calendário semanal mantém a composição aceitável, mas os 5 ecrãs de gestão ainda revelam **estilos não aplicados**: Início com ações rápidas e cartões semanais cinzentos em 2 linhas e sobreposição nutricional; Receitas com banner ~390 px físicos e catálogo abaixo da dobra; Família com tabela sem separadores, botões de cabeçalho cinzentos e contagens coladas; Compras com 4 indicadores em 3+1 e lista fora do ecrã; Despensa com indicadores em texto vertical sem cartões.

**Diagnóstico:** as capturas têm 1535 px físicos de largura e o browser pode ter viewport efetivo de ~1024 px CSS ao usar zoom 150%. As regras estruturais da v2.1.8 tinham sido concentradas em `@media(min-width:1101px)`; num viewport CSS intermédio (761–1100), o navegador aplicava a composição herdada e falhava apesar de os testes 1280×631 passarem. A solução não é repetir CSS apenas para a largura física do screenshot.

**Implementação:** `apps/web/src/compact-desktop-reference.css` carregado por último em `main.tsx`, com regras exclusivamente para 761–1100 px CSS. Preserva as rotas, drawers, dados, comparações por membro, fotos de receitas e Semana. Impõe 4 atalhos, 3 cartões semanais, 4 indicadores de Compras e Despensa, compacidade da faixa de Receitas, comparação da Família com tabela transparente e divisão nutricional do Início. Contrasta com os 1672×941 ilustrativos sem fabricar produtos.

**Validação:** `approved-reference-viewport.spec.ts` recebe capturas dark/light para Início, Receitas, Família, Compras e Despensa em 1024×505 e asserts de grelhas/altura/fundo, além dos testes anteriores. Este lote não é paridade fotográfica automática; aceitar apenas após Web CI, API CI, UX E2E e inspeção visual real no browser do utilizador. Não modificar o calendário semanal aprovado para resolver os outros ecrãs.

## v2.1.13 — Início apenas, dois modos responsivos (21/11/2026, 16:40)

Pedido: corrigir uma página de cada vez e abandonar o ajuste ad hoc por tamanhos de screenshot. A captura real da v2.1.12 confirma cartões cinzentos em 2×2 dentro de Ações rápidas, 3 cartões semanais quebrados e informações nutricionais sem espaçamento.

**Causa encontrada no código, e não inferida por zoom:** `screen-reference.css` mantém em `@media(min-width:1101px) and (max-height:680px)` uma regra `.nf-home .nf-home-shortcuts {display:grid;grid-template-columns:repeat(2,minmax(0,1fr))}`. O painel contém exatamente 2 filhos: título e grelha de 4 ações. Assim a grelha interna ocupa **só metade da largura**. As alterações anteriores concentraram-se no estilo da grelha interna e dos botões, sem corrigir o pai. Isso explica o efeito 2×2 no desktop.

**Solução v2.1.13:** no stylesheet final `compact-desktop-reference.css`, duas composições exclusivas:
- Desktop CSS >= 761: painel exterior `display:flex;flex-direction:column`; grelha de ações com 4 colunas ocupando 100% do espaço; planos semanais 3 colunas reais; cartões com cores do tema e alturas via `clamp()`; apresentação do painel nutricional em duas colunas, separando nome/consumo/planeado e pessoas.
- Mobile CSS <= 760: ações 2 colunas; cartões semanais 1 coluna; nutrição e pessoas empilhadas.
Nada foi alterado nas páginas Semana, Receitas, Compras, Família ou Despensa neste lote; sidebar única, drawers e dados reais preservados.
- `approved-reference-viewport.spec.ts` agora verifica a **propriedade computada do contentor exterior** `display:flex` (não só a contagem de botões nem a variável CSS) em 1024px e 1280px CSS, além de screenshots.

Princípio adotado: não encolher uniformemente fonte/alvos de toque; usar apenas dois layouts e tamanhos fluidos com limites de leitura. Manter a Semana aprovada sem mudanças.
**Estado:** aguardam Web/API/UX E2E e confirmação visual no browser real; não declarar paridade pixel a pixel.
