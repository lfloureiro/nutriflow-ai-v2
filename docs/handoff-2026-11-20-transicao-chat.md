# HANDOFF — NutriFlow AI v2: continuidade no próximo chat (20/11/2026)

> Documento de passagem preparado por solicitação do utilizador. **A tarefa deste turno é preservar contexto; não alterar UI sem primeiro confrontar o HTML de referência.** O utilizador quer continuar a revisão e implementação visual e funcional, menu a menu, ecrã a ecrã, no PR existente. Não dizer que a equivalência visual está atingida.

## Repositório / branch / validação

- Repositório privado: `lfloureiro/nutriflow-ai-v2`.
- Branch de trabalho: `codex/ux-drawer-next-batch-20261119`.
- PR: **#76 draft** (https://github.com/lfloureiro/nutriflow-ai-v2/pull/76). **Não fazer merge para main** sem aprovação explícita.
- Versão em `apps/web/package.json`: **v2.0.73** (X.Y.Z, Z para correções e lotes sem pedir confirmação constante).
- Commit funcional v2.0.73 antes deste handoff: **`3dc7bf7e2a994d1e157b3c1ebaa779f50046541f`**. Confirmado **Web CI / API CI / UX E2E synthetic 3/3 success** neste SHA. Não transportar a afirmação 3/3 para commits documentais subsequentes sem verificar a execução correspondente.
- Build v2.0.72 local Windows confirmado pelo utilizador, `✓ built`, porém havia aviso Vite de chunk >500kB. v2.0.73 separou rotas com React.lazy, Web CI: **231 testes**, build e TS passaram, maior JS gerado **228,56kB** sem aviso de 500kB.
- Local Windows: `D:\Python\nutriflow-ai-v2`, frontend Vite `127.0.0.1:5173`, API FastAPI `127.0.0.1:8000`, PostgreSQL em Docker. Frontend no terminal com Vite ativo; **não iniciar duplicados** nem matar API/DB. `.cache/ux-preview.json` pode ter PID desatualizado. Uma versão anterior teve ecrã branco por colisão Windows `NextMealHero.tsx` vs `nextMealHero.ts` (diferiam só no case); corrigido para `NextMealBanner.tsx` + `nextMealSelection.ts`. Não repetir.

## Referência visual — decisão DO UTILIZADOR

- Referência primária e obrigatória é **`Casa_a_Mesa_High_Fidelity.html`**, conhecido no Windows como `C:\Users\Luis Loureiro\Downloads\Casa_a_Mesa_High_Fidelity.html`, com fragmentos como `#week`. Se o HTML não estiver montado/acessível no próximo chat, pedi-lo ao utilizador ou recuperá-lo dos anexos/ficheiros disponíveis. **Não inferir valores exatos a partir de memória, screenshot ou rascunhos**.
- A referência funcional é a aplicação em `apps/web/src`: manter funcionalidades e dados reais, drawers de contexto, regras nutricionais, FODMAP, preferências individuais/familiares, receitas/ingredientes, substituições, compras, perfis, etc. Não copiar dados demo do HTML para produção. UX visual do protótipo + capacidades reais do produto.
- O utilizador exige **igualdade de cores, luz, fontes, dimensões, bordas, proporções, ícones e brilho**, não aproximações sucessivas. Comparar usando o mesmo viewport, zoom, escala e tema, abrir o HTML **e a aplicação simultaneamente**, auditar DOM/CSS do HTML de referência e usar *computed styles* no Chrome. Definir variáveis canónicas de design e ajustar **globalmente** antes de casos particulares.
- Revisão **ecrã a ecrã, menu a menu**, dando ao utilizador um protótipo visual para aprovar antes de implementar cada próximo ecrã. «A nossa semana» foi aprovada em versão hero-first e tem ajustes feitos; ainda falta correspondência exata e auditoria light/dark. Não avançar para ecrã 2 sem resolver essa divergência ou decisão do utilizador.
- Cores atuais em `apps/web/src/design-tokens.css`: light bg `#f6f5f0`, surface `#fffefa`, ação `#285a40`; dark bg `#19191b`, surface `#222225`, ação `#d8b28c`. **Não presumir que coincidem com o HTML em todos os seletores**; grande parte do CSS tem overrides diretos. Fonte-base em `apps/web/src/styles.css`: `"Segoe UI", Inter, ui-sans-serif, system-ui, -apple-system, sans-serif`. Pode diferir da fonte usada no HTML; comparar família, carga da fonte, peso, line-height e anti-aliasing. Não resolver apenas com hex.
- Screenshots comparativos mais recentes (20/11, 22:44–22:50) no chat anterior mostram **protótipo dark**, **semana implementada v2.0.72** e **Início implementado v2.0.72**. Novos uploads devem ser examinados visualmente; o anexo do ecrã Início mostra o mesmo menu com tipografia/fundos diferentes dos da Semana. Anexos do chat podem precisar de reenvio no novo chat, caso não apareçam.

## Descoberta técnica importante: MENU COMUM MAS ESTILOS DIFERENTES

- Navegação lateral e topbar são **renderizadas UMA vez** no `App.tsx`:
  - `<aside className="side-nav">`, `<nav className="primary-nav">`;
  - entradas Início, A nossa semana, Receitas, Família, Compras e Despensa;
  - cartão `side-nav__ai` «Inteligência à mesa» -> modo de recomendação;
  - `side-nav__family` e `shell-topbar`.
- A wrapper usa **`app-shell--meals` apenas se `view === "meals"`**, e `shell.css` (zona final, v2.0.72) define *especificamente nessa classe*:
  - `.app-shell--meals .side-nav__ai`, `.side-nav__ai-heading`, etc.; 
  - `.app-shell--meals .side-nav`, `.primary-nav`, `.nav-item`, `.side-nav__family` em desktop;
  - `.app-shell--meals .shell-main` e `.shell-topbar`.
- **Resultado:** o HTML/componente de menu é partilhado, mas o aspeto é inconsistente por vista. O utilizador detectou a diferença entre imagens «Semana» e «Início». **Próxima intervenção necessária:** promover estilos do menu e topbar a um **único design system aplicado a todas as rotas**, extrair opcionalmente `AppShell/Sidebar` de `App.tsx` para testes/componentização, e reservar classe de rota apenas para layout interior da semana, nunca para branding/sidebar. Definir e testar invariantes em rotas `home/meals/people/house/shopping/more` e mobile.
- Há vários níveis de regras sobrepostas: `styles.css`, `shell.css`, `visual-polish.css`, `ux-foundation.css`, `ux-planning.css`, `next-meal-hero.css`; `main.tsx` carrega todas. Cuidado com CSS specificity, `!important`, duplicações de cartões e cores hardcoded, especialmente `:root[data-theme="dark"]`. Fazer inventário de *computed styles* e **eliminar overrides conflitantes**, não adicionar patches intermináveis.

## Semana — decisões fechadas

- Estrutura visual: **carta «Próxima refeição» → Semana anterior/Esta semana/Semana seguinte → grelha da semana**. Sem faixas informativas gerais nem «Outras vistas», «Hoje», «Semana» e «Recomendar» visíveis na página da semana. «Dia» pertence ao Início; recomendações dedicadas noutra área (o cartão AI abre a vista própria). Não eliminar fluxos antigos, apenas reencaminhar.
- A carta superior dinâmica (em `NextMealBanner.tsx`, lógica de horários em `nextMealSelection.ts`): próxima refeição do fuso da família; se guardada, mostrar e abrir; se vazia, **motor real de propostas familiares**, com gostos, restrições, nutrição, flow/histórico, preferências e presenças quando disponíveis. Sem gravação automática; rever/adaptar/alternar. Dados insuficientes = estado honesto, não inventar refeição. Falta integrar de forma completa **presenças por slot** e cobertura fotográfica real.
- Imagens: início de catálogo curado com licenças/fontes, fallback local `/images/shared-meal.svg`, não equiparar foto ilustrativa a receita real. **Cobertura completa ainda pendente**.
- `WeeklyProposalPreview.tsx` tem `simpleWeekView`, cards de 7x4, quatro linhas identificadas à esquerda, estado de revisão e drawers de contexto. Em `ux-planning.css` secção `nf-week-map-final` adotada grelha `70px + 7 colunas`, gaps 7px, min-height 112px, radius 11px, título 11px e etiqueta 9px (valores registados durante comparação anterior). **Ainda não está visualmente idêntico** ao HTML original de referência (comparar tamanhos, bordas, cores reais por estado e tipografia).
- O utilizador marcou previamente com X: tirar a barra geral «As propostas exigem confirmação...» e o menu intermédio «Outras vistas e ferramentas». Feito na v2.0.71. Não restaurar.

## Roadmap e pendências da nova sessão — ORDEM DE PRIORIDADE

1. **Auditoria exata do protótipo**: reabrir HTML `Casa_a_Mesa_High_Fidelity.html`; extrair *tokens*, fontes, regras de `sidebar`, `header`, `week`, *computed style* dos cards, contraste claro/escuro, spacing, line height, radius. Comparar com a app. Se faltar o HTML, **solicitar o ficheiro**, sem declarar igualdade com base em screenshots.
2. **Uniformizar o shell comum**: remover os overrides `.app-shell--meals .side-nav*`, `.app-shell--meals .primary-nav` etc. e aplicar o estilo aprovado ao menu **em TODAS AS VISTAS**. Manter `.app-shell--meals` somente para o conteúdo central da página semanal. Criar regressão que prove paridade dos estilos do shell em rotas e light/dark.
3. **Corrigir diferenças cromáticas/tipográficas verdadeiras**, via tokens de origem do HTML e folhas globais, sem recorrer a paleta aproximada. Validar fontes efetivamente carregadas e não misturar Segoe UI com outra fonte do protótipo.
4. **Auditar semana light/dark a 1440/1024/768/390 e zoom 200%**, grelha/carta/badges/ativação; se necessário fazer screenshots com testes de navegador em ambiente sintético, sem expor dados familiares reais. A app a executar em Windows não é diretamente visível por GitHub; pedir nova captura ao utilizador apenas quando for útil.
5. Conservar roadmap e documentação: `docs/handoff-2026-11-19.md`, `docs/ux/roadmap-v2.1.0-rc.md`, `docs/ux/lote-seguinte-drawer-2026-11-19.md`, `docs/ux/aceitacao-manual-v2.1.0.md` e **`docs/ux/proxima-refeicao-decisoes-2026-11-20.md`**. Atualizar em cada lote, PR #76 draft. Só pedir teste manual na mudança de X ou Y ou quando o utilizador escolhe fazê-lo; Z para patches e correções.
6. Após concluir a semana e o shell: seguir **Início, Receitas, Família, Compras, Despensa**, um ecrã de cada vez com proposta visual para aprovação. Nunca perder funções da app anterior.

## Restrições de trabalho e segurança

- Utilizador quer implementação real, sequencial, sem reportes a cada patch. Não prometer trabalho assíncrono. Trabalhar o máximo possível no turno, sem tocar em serviços ou DB reais.
- Nunca alterar `main`, fazer merge de PR, eliminar dados, receitas, plano, API ou modificar constraints nutricionais sem aprovação explícita.
- Proteger Windows case-insensitivity: não criar dois ficheiros cujo nome difira apenas na capitalização.
- CI: Web / API / UX E2E **no mesmo SHA** antes de alegar 3/3. CI sintético não equivale à validação visual real.
- Vite 5173 em execução; não criar segunda instância `npm run dev` nem matar os serviços. Fazer `git status --short` + branch antes do `git pull --ff-only` do branch; se alterações locais, parar e resolver em vez de sobrescrever.

## Prompt recomendado para colar no próximo chat

«Continua o desenvolvimento de NutriFlow AI v2, PR #76 draft, branch `codex/ux-drawer-next-batch-20261119`. Lê primeiro `docs/handoff-2026-11-20-transicao-chat.md`, `docs/handoff-2026-11-19.md` e a documentação UX. A versão validada é v2.0.73, commit `3dc7bf7e2a994d1e157b3c1ebaa779f50046541f`, 3/3 CI verdes. Há um problema de paridade do protótipo: o menu é único em App.tsx, mas os CSS `.app-shell--meals` causam aspeto diferente na Semana e no Início; as cores e fontes continuam diferentes do HTML `Casa_a_Mesa_High_Fidelity.html`. Quero equivalência visual exata em light e dark. Reabre o HTML, obtém os CSS reais e as fontes, uniformiza primeiro o shell em todas as rotas e compara a grelha semanal a nível de computed styles. Não inventes cores nem faças apenas patches aproximados. Não percas funcionalidades, não mexas em dados reais, mantém PR draft e docs/CI atualizados. Depois retomamos a revisão visual ecrã a ecrã.»

## Continuidade desta sessão — v2.0.74 (20/11/2026)

- Reaberto o HTML exato `Casa_a_Mesa_High_Fidelity.html` da biblioteca do projeto e extraídas regras e tokens do CSS inline. A auditoria e matriz de propriedades estão em `docs/ux/auditoria-shell-prototipo-2026-11-20.md`.
- Removidas do `shell.css` as diferenças de sidebar, AI e topbar sob `.app-shell--meals`; mantidas regras de layout exclusivamente interiores da página semanal.
- Criada `apps/web/src/shell-prototype.css` como última importação CSS; largura sidebar 230px, navegação e cabeçalho comuns a todas as rotas, conforme a fonte original. A estrutura do menu continua partilhada em `App.tsx`.
- `styles.css`: corpo DM Sans 14px/1.55, títulos Manrope; `index.html`: carga das famílias a partir de Google Fonts; `design-tokens.css`: acento decorativo e sombras do HTML de referência. Os seis menus, drawers, decisões da carta «Próxima refeição», dados e API permanecem intactos.
- Adicionado `shellPrototype.test.ts` para proteger invariantes estáticos de styling e importação global.
- **Não declarar paridade pixel a pixel**: não houve inspeção de `getComputedStyle` simultânea nos dois documentos com o mesmo navegador, viewport e fonte carregada. O original declara fontes mas não as carrega explicitamente.
- PR #76 **draft**, `main` intocada; nenhuma alteração em serviços locais ou base de dados real. Versão web 2.0.74. Confirmar os três CI no SHA final antes de marcar como funcionalmente validada.
- Próxima intervenção após CI: auditoria visual da Semana light/dark (1440/1024/768/390 + 200%) e, depois, revisão de Início, Receitas, Família, Compras e Despensa.
