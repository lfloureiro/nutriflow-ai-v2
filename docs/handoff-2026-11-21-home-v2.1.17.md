# HANDOFF — NutriFlow AI v2, Home visual parity, 21/11/2026

**Este documento substitui a versão antiga do handoff para decisões relacionadas com o Início.** Consultar também `docs/ux/auditoria-critica-imagens-aprovadas-2026-11-21.md` para cronologia, limitações e evidências.

## Localização e disciplina do trabalho

- Repositório: `lfloureiro/nutriflow-ai-v2` (privado).
- PR **#76 draft**: https://github.com/lfloureiro/nutriflow-ai-v2/pull/76
- Branch única: `codex/ux-drawer-next-batch-20261119`.
- Ambiente do utilizador: Windows, `D:\Python\nutriflow-ai-v2`, frontend Vite `http://127.0.0.1:5173`, API local `:8000`, PostgreSQL.
- **Não fazer merge, mexer na `main`, reiniciar serviços locais ou alterar dados reais sem ordem explícita.**
- Versão de UX em `apps/web/package.json`: **v2.1.17**. Política do utilizador: `X.Y.Z`, incrementar `Z` em lotes e correções sem pedir aprovação a cada commit; pedir teste em pontos significativos.
- Foco atual **exclusivo no Início**, uma página de cada vez. **A nossa semana** foi aprovada visualmente, não desfazer a grelha e as alturas dos cartões.
- O utilizador quer correspondência visual rigorosa, não só testes a passar. Garantir desktop e mobile como duas composições, dimensões fluidas dentro de cada uma, sem microajustes de breakpoint por screenshot.

## Referências obrigatórias

1. **Referência aprovada original**: `docs/ux/references/inicio.png` no pacote de referências / Biblioteca; manifesto `docs/ux/references/manifest.json`, SHA-256 `9d4537597267bebdeaadadb1bc35d13f236e231b077354b3664caac830beec15`, 1672×941. As referências para Receitas/Família/Compras/Despensa e seus hashes também estão no manifesto. Os PNG ainda não estão comitados como binário, porque o conector GitHub só escreve UTF-8. **Não fingir que estão no Git.**
2. Uma nova imagem conceptual de Início e uma prancha comparativa foram geradas no chat em 21/11, após o utilizador pedir «mostra-me as imagens e implementa». São auxiliares e contêm **valores fictícios (72% e macronutrientes)** e fotografias ilustrativas; **não sobrepõem o PNG aprovado** nem devem definir os valores em produção.
3. Última imagem real do utilizador, v2.1.16 (21/11 às 17:17): as quatro ações, três cartões semanais e avatares estavam bem mais próximos da referência; a composição ainda não apresentava o grande anel nutricional/barras de progresso e as fotos/alguns textos diferiam.
4. Objetivo de comparação: mesma hierarquia (hero → quatro refeições + progresso nutricional → ações + planos), card density, bordas, cores, fontes, ícones e ajuste ao viewport do Chrome. O CSS viewport real medido foi **1280×631**, noutros cenários 1229×610 ou 1024×505; screenshots físicos têm dimensões diferentes devido ao zoom/escala.

## Implementação v2.1.17

- `apps/web/src/FamilyHome.tsx` reorganizou o Início (sem alterar os dados das APIs nem os callbacks).
  - Hero usa `nextFamilyMeal()`, `resolveMealHeroImage()` e crédito de fonte; não substituir a próxima refeição real por salmão ilustrativo.
  - «O dia de hoje»: 4 cartões de refeição com foto apenas se houver imagem verificada, ícones, nome, estado real, fallback para refeição vazia, clique abre plano da data.
  - «Progresso nutricional da família»: anel de **percentagem de pessoas com consumo registado** (não atingir uma meta clínica), 4 barras por membro de consumo/energia planeada quando os dois dados existem, estado sem registos. Tipo `FamilyDashboardNutrition` fornece energia, não macronutrientes; não inventar Proteína, Hidratos e Lípidos nem mostrar `72%` fictícios.
  - Membros mantêm acesso a `onOpenPerson` via chips com avatar/nome no rodapé nutricional. Com muitos membros, verificar overflow responsivo.
  - Ações rápidas mantêm os callbacks existentes; `onOpenRecipes` **navega** para Receitas (não é um gerador de receitas).
- `apps/web/src/home-v3.css` mantém o styling v3 isolado e acrescenta layout editorial v4 sob `.nf-home-reference-v4`: desktop 2 colunas com hero full-width, quatro refeições à esquerda, nutrição à direita, ações e planos abaixo; mobile empilhado.
- `apps/web/e2e/approved-reference-viewport.spec.ts` e `shell-visual-parity.spec.ts` adaptados aos chips `.nf-home-family-chip` em vez de `.nf-person-line`; mantém asserts de geometria e quatro cartões/3 semanas/estilos calculados.
- `docs/ux/auditoria-critica-imagens-aprovadas-2026-11-21.md` é o registo de decisões e observações.
- Outros ecrãs **não foram editados neste lote**. Grelha semanal não foi alterada.

## Estados e validação

- **Não declarar paridade pixel a pixel** nem «pronto para testar visualmente» antes de confirmar Web CI, API CI e UX E2E no SHA final **e** olhar para screenshot real do Início.
- CI no momento da criação deste documento: workflows no SHA de código `46013df7` iniciados, ainda pendentes; commits posteriores de documentação não alteram runtime. Consultar https://github.com/lfloureiro/nutriflow-ai-v2/actions .
- A execução E2E anterior testava classes `.nf-person-line` antigas; o lote atual atualizou os seletores. Se houver erro, ler logs do job, corrigir a aplicação quando for bug real, nunca reduzir a exigência para esconder problema. Os workflows foram ajustados para PR/push na main, evitando duplo disparo.
- Testar pelo menos **1280×631 e 1672×941 desktop**, **390×844 mobile**, ambos dark/light, 4 perfis populados e família sem registos. Verificar sobreposição, conteúdo essencial no primeiro ecrã, 4 ações e 3 planos em desktop, navegação dos chips, botão da próxima refeição, foco dos drawers e acesso ao conteúdo real.
- A imagem conceptual usa `Gerar receitas`; o callback atual abre o catálogo. Preservar ação real/rotulagem coerente.

## Pendentes por ordem

1. Confirmar CI final e corrigir qualquer falha relevante; comparar captura Chromium com o PNG aprovado.
2. Corrigir apenas o Início até ter revisão visual do utilizador. Os dados nutricionais atuais não sustentam barras agregadas por macronutriente; propor apenas UI com ausência de dados explícita ou extensão real de API, sem valores falsos.
3. Confirmar fotos autorizadas/verificadas de refeições e crédito discreto, nunca apagar proveniência.
4. Rever contraste e tipografia light/dark, responsividade mobile, 4 membros legíveis, scroll de listas maiores e foco em drawers.
5. Quando Início aprovado: Receitas → Família → Compras → Despensa, confrontando os PNG aprovados um a um, sem remover funcionalidades.
6. Comitar os 5 PNG originais como binários numa sessão com Git local/Work se houver acesso a bytes, validando SHA-256 do manifesto. Conector Github UTF-8 não carrega PNG diretamente.

## Como iniciar um novo chat sem perda

> Continua o desenvolvimento **NutriFlow AI v2** a partir de `docs/handoff-2026-11-21-home-v2.1.17.md`, `docs/ux/auditoria-critica-imagens-aprovadas-2026-11-21.md`, `docs/ux/references/manifest.json` e PR #76 na branch `codex/ux-drawer-next-batch-20261119`. Verifica primeiro o último SHA e Web/API/UX E2E. O Início v2.1.17 é o foco; a Semana está aprovada, não a alteres. O alvo visual é o PNG original `inicio.png` SHA-256 `9d453...`, não os valores ilustrativos 72% da imagem conceptual. Continua a implementar e documentar, só pede teste quando houver alterações verificadas no navegador. Não tocar em main nem dados reais.

## Atualização — 21/11/2026, Início v2.1.18

**Versão mais recente `apps/web/package.json`: v2.1.18**, substitui a menção a v2.1.17 no topo deste documento. Última captura do utilizador v2.1.17 às 17:46, com três marcações verdes: meta do hero cortada em baixo; fallback do jantar com ícone livro em vez de imagem/prato; cartões semanais com datas cortadas. Implementada correção em `FamilyHome.tsx` (`cloche` como fallback) e `home-v3.css` (meta na linha da data, fundo dos cartões de semana com min-height 78px e fila inferior 165px). Teste Playwright estendido para assegurar que a meta e as datas ficam dentro dos seus contentores. **UX E2E v2.1.17 falhou** com cartões semanais de 32,71875px e cartões de refeição 383,984375px a 1280×700; estes são bugs reais corrigidos na distribuição das linhas, nunca desativar testes. Revalidar o SHA de v2.1.18 no GitHub antes de continuar. Não mexer na Semana, nem usar conteúdo fictício do protótipo.


## v2.1.19 — 21/11/2026, 18h: diferenciação de planeado/consumido e lote de imagens

Pedido do utilizador: manter a correção de imagens e alinhamento, usar novas imagens geradas, e criar calorias estimadas para dias anteriores para que os gráficos possam ser avaliados. **Não adulterar registos reais**.

- Nova função pura `apps/web/src/homeNutritionPresentation.ts`: em datas passadas, quando existe energia planeada mas não consumo positivo, cria **apenas na interface**, e deterministamente por data+id de pessoa, uma estimativa de 62–95% do planeado. Nunca escreve na API, BD ou histórico. Os números são marcados `(sim.)` e há aviso inequívoco «Valores de demonstração … Não são refeições consumidas ou registos clínicos». Consumos reais sobrepõem-se sempre à simulação.
- Em **hoje**, se não existem registos de consumo, o anel mostra, em vez de um falso 0% de ingestão, a percentagem **dos horários de refeições planeadas já decorridos**, rotulada «do horário», e apresenta «sem consumo confirmado». Barras individuais só representam consumo/plano quando comprovado; energia planeada aparece como meta operacional, não meta clínica. Após registos reais, mantém o indicador «com registo».
- `FamilyHome.tsx` destaca o cartão correspondente à próxima refeição selecionada, com borda e fundo dourados; `home-v3.css` fixa uma estrutura interna de label/título/estado, ícones em ações e alturas controladas. Não modifica Semana.
- Produzido pacote de 7 imagens fotográficas ilustrativas em `WebP`: bifanas, escalopes, frango rápido, salmão, torrada mista, aveia com iogurte e banana, banana e frutos secos. Arquivo da conversa **`nutriflow-imagens-v2.1.19.zip`** com instalador PowerShell e manifesto SHA-256. Os **binários não estão no GitHub** porque o conector só suporta UTF-8. É necessária uma instalação local (ou `git add` a partir do Windows) para que carreguem no Vite; na ausência, os `img` retomam as fotos Wikimedia ou um fallback neutro. `mealHeroImages.ts` usa correspondência exata de receitas, preserva fotos explícitas, identifica IA. `apps/web/public/images/generated/README.md` documenta os sete nomes.
- Novos testes `homeNutritionPresentation.test.ts` asseguram determinismo, não mutação do consumo verdadeiro, data atual sem simulação e respeito ao consumo real; `mealHeroImages.test.ts` verifica correspondência exata, proveniência e fallback.
- **Estado:** código v2.1.19 na branch PR #76; CI precisa confirmar o último commit. O screenshot real do Chrome e a paridade com `inicio.png` continuam por verificar. Não declarar as fotos instaladas no GitHub ou no computador do utilizador.

## Atualização v2.1.20 — imagem bifanas integrada no PR #76

A primeira imagem gerada foi incorporada diretamente na branch Git: `apps/web/public/images/generated/bifanas-com-natas.webp` (320×240, 4962 bytes, SHA-256 `38650895acfac74dbaaeb0546a868a06b44705c47d3b60d3831cb892f88b41ca`). O seletor `mealHeroImages.ts` já usa esse caminho para «Bifanas com natas», no banner e no jantar, com origem identificada como «Imagem ilustrativa · IA». Foi adicionado teste de integridade binária. Esta atualização **substitui** as indicações anteriores de que *nenhuma* fotografia fora colocada no Git. As outras 6 fotografias permanecem no pacote de instalação local e não foram comitadas. Manter a Semana aprovada sem alterações. Verificar no Chromium / screenshot do utilizador após atualizar branch; não declarar aceitação visual com base apenas no CI.
