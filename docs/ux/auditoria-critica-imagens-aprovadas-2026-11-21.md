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
