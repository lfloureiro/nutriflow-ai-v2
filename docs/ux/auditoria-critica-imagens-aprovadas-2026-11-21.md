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
