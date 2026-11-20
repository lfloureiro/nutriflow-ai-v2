# NutriFlow AI — sequência de entrega após v2.0.25

Estado inicial (19/11/2026): v2.0.25 / `630d56b0337820f1d7c182485224d3d1c535b826` com **Web CI, API CI e UX E2E aprovados**. O utilizador confirmou que o fluxo de drawer e mapa semanal voltou a funcionar e pediu continuidade sem interrupções até ao primeiro teste manual consolidado.

## Contrato de UX que não pode regredir

- A página/lista/grelha permanece montada; detalhes e edição abrem **um único drawer**.
- Fecho/cancelamento sem alteração não deve disparar recarregamento, substituir a página por spinner nem abrir outro painel intermédio.
- A navegação e os deep links preservam a semana/dia/item; Escape e fechar regressam ao mesmo contexto.
- Não se perdem requisitos anteriores: quatro refeições/dia, perfis, saúde, receitas/ingredientes e substituições, nutrição por pessoa, FODMAP com incerteza, avaliações 1–5, compras, i18n/temas, segurança de dados.

## Blocos seguintes, por dependência

| Marco | Foco | Prova mínima |
| --- | --- | --- |
| 2.0.26 | Abertura/fecho estável do editor de refeições sem pedidos redundantes | E2E cancelamento sem re-fetch; CI 3/3 |
| 2.0.Z seguintes | Auditar ações e editores secundários ainda inline (despensa, compras, avaliações, preferências); manter página original | E2E com uma modal, retorno direto e rascunhos protegidos |
| 2.0.Z seguintes | Painel individual: restrições, tolerâncias e fonte/validade do plano profissional, com estado desconhecido; não inferir tratamento a partir de diagnósticos | Testes de restrições/proveniência e isolamento entre pessoas |
| 2.0.Z seguintes | Nutrição por refeição/porção versus plano profissional efetivo e sugestões de adaptação explicitamente não certificadas | API e E2E sintéticos de elegibilidade, confirmação e compras |
| 2.0.Z seguintes | Navegação URL/back/forward, i18n, desktop/tablet/mobile, temas e acessibilidade | Regressões por viewport; auditoria visual e zoom 200% antes do RC |
| 2.1.0-rc | Congelar comportamento, comparar com protótipo aprovado, checklist completa e comando PowerShell verificado | Web/API/E2E **verdes no mesmo SHA**, zero bugs bloqueantes e handoff declarado PRONTO PARA TESTE |

## Fronteiras de versão

- **Z:** alterações incrementais e correções sem solicitação de teste manual ao utilizador.
- **Y:** primeira verificação manual consolidada na mudança para 2.1.0, apenas quando os critérios acima tiverem evidência.
- **X:** reservada para alterações de contrato/arquitetura maiores que necessitem de plano de migração e aprovação.

## Comunicação e repositório

Trabalhar em `codex/ux-drawer-next-batch-20261119` / PR #76 **draft**. Não fazer merge para `main` sem aprovação. Não correr testes destrutivos na base familiar real. Manter `docs/ux/aceitacao-manual-v2.1.0.md` como lista oficial e o handoff sincronizado com SHA/CI exatos. O monitor de preparação já configurado para NutriFlow pode informar quando os requisitos de teste manual estiverem satisfeitos; não prometer execução contínua autónoma fora de tarefas agendadas.

## Estado de execução — 20/11/2026

- **v2.0.30** (SHA `277e87f898064919fd95e361fe59e085797debe8`): Web CI, API CI e UX E2E **verdes no mesmo commit**. Correções de data selecionada em mobile e ausência de deslocação do drawer a 320px.
- **v2.0.31**: fluxo de revisão de substituições passa a um único drawer a partir da lista; modo de receita fixa preserva renderização contextual; E2E de navegação/FODMAP adicionado. **Aguardar CI do SHA final.**
- **Pendentes prioritários:** avaliações por pessoa/receita sem confundir gosto com restrições; fontes e validade das restrições individuais e plano profissional; comparação de nutrição por porção com metas de refeição; revisão de navegação e acessibilidade; zoom real 200% e evidência visual antes do marco 2.1.0.
- **Obrigação de documentação por patch:** atualizar este roteiro, `docs/ux/lote-seguinte-drawer-2026-11-19.md` e a secção de estado do handoff, registando SHA e estado dos três gates sem declarar como concluído o que não foi testado.

## Estado de execução — 20/11/2026, patch v2.0.32

- **v2.0.31**: Web CI e API CI verdes; UX E2E falhou num cenário por duplicação do nome da receita em dois títulos no drawer de revisão. Não marcou o gate 3/3.
- **v2.0.32**: título duplicado removido; preferências de receitas descrevem de forma explícita o score de gosto, separado de segurança/nutrição/FODMAP; teste API sintético verifica médias por pessoa e limpeza. **Aguardar os três gates no último SHA.**
- Próximos blocos após gate verde: avaliação nutricional individual e proveniência/validade do plano profissional; melhoria da experiência de ratings no contexto das receitas; inspeção visual responsive/zoom 200%, seguida do candidato 2.1.0.

## Estado de execução — 20/11/2026, patch v2.0.33

- v2.0.32: Web CI, API CI e UX E2E **verdes no mesmo SHA** `b39005f478865a8a3f24d5b89aab146edae24474`.
- v2.0.33: o painel individual de adequação nutricional distingue cobertura de regras, dados desconhecidos, orientações não avaliadas e bloqueios obrigatórios. Proveniência expandível sem inventar fonte; testes unitários adicionados. **CI do SHA final ainda por confirmar.**
- Próximos blocos após gate verde: ligação entre avaliação individual e seleção da refeição contextual, melhor leitura de tolerâncias e proveniência de condições, comparação com plano profissional por porção; acessibilidade e zoom 200% antes do RC.
- Documentação, testes e SHA/CI atualizados por patch. Nenhum dado pessoal no GitHub, nenhuma promoção de PR draft para `main` sem aprovação.

## Estado de execução — 20/11/2026, patch v2.0.34

- **v2.0.33:** três gates **verdes** no SHA `c5fc2e4432deb933016fcc7b426f00b3759129e0`. Evidência de adequação nutricional separa regras avaliadas, desconhecidas e fontes registadas.
- **v2.0.34:** saúde individual apresenta origem e intervalos temporais explicitamente desconhecidos quando em falta e avisa quando um estado de confirmação profissional não dispõe de referência verificável. Testes unitários e CSS responsivo incluídos. **Validação do SHA final ainda pendente.**
- **Pendentes prioritários:** ligar a seleção contextual da refeição à avaliação individual; comparar porções com orientação profissional efetiva; distinguir tolerâncias declaradas de restrições médicas; rever zoom 200% e equivalência visual com o protótipo antes do RC.

## Entrega agrupada — 20/11/2026, versões 2.0.35 a 2.0.37

- **v2.0.34**: Web CI, API CI, UX E2E **3/3 aprovados** no SHA `aee0e83763f2ee9ffb0909bda40390fd7152bf87`.
- **v2.0.35**: composição energética/nutricional da porção avaliada sem preencher nutrientes desconhecidos. Teste unitário e CSS responsive.
- **v2.0.36**: fonte, referência documental e versão dos planos profissionais, distinguindo fonte declarada de verificação profissional. Teste unitário e CSS.
- **v2.0.37**: invalidar avaliação e propostas assíncronas quando muda pessoa, data, refeição, receita ou porção. **Exigir CI 3/3 no SHA final**, não declarar patches anteriores validados de modo independente.
- **Pendentes:** teste E2E com atraso artificial e troca de contexto; referências profissionais por pessoa; comparação nutricional em refeições concretas; inspeção visual zoom 200%, i18n e aceitação manual v2.1.0.
- Manter o documento de lote `docs/ux/lote-seguinte-drawer-2026-11-19.md` como registo por patch e este roteiro como fonte de prioridade.

## Correção durante validação do lote 2.0.35–2.0.37 (20 novembro 2026)

- No SHA `ee778989f56d897a5a9cec2865a1c64ab857f21c`, o Web CI falhou por **TypeScript TS2352 num fixture parcial** dos testes da composição da porção (cast direto de objeto parcial para `MealPlanFitResult`).
- Corrigido o teste com cast explícito `unknown`, mantendo a tipagem de produção; a apresentação nutricional passa ainda a tratar strings vazias como **dados desconhecidos**, e não zero. Teste adicional para esse caso.
- Publicados commits corretivos `8aa8208`, `33eeae5` e `cefae3d`. **Não marcar a entrega como aprovada** sem os três gates verdes no último SHA.

## Estado de execução — 20/11/2026, entrega agrupada 2.0.38–2.0.39

- **v2.0.37:** CI Web/API/UX E2E **3/3 aprovado** no SHA `bab5ef8ae0928f45ca6c87d55533bc028eeef6aa`.
- **v2.0.38:** atalho Refeições de hoje → Nutrição na mesma pessoa, respeitando o tipo de refeição, sem abrir um segundo drawer.
- **v2.0.39:** seleção da receita obrigatória no contexto (nunca inferida do título), quantidade a confirmar e opção de limpar seleção, com remontagem do avaliador entre refeições para eliminar estados antigos. E2E sintético de contexto adicionado; **aguardar 3 CI verdes no SHA final**.
- **Pendentes para RC 2.1.0:** comparação mais direta com a porção planeada efetiva e restrições profissionais reais, regressões de rede atrasada e dados insuficientes, equivalência visual com protótipo, zoom 200%, temas/i18n e checklist de acessibilidade.

## CI de confirmação v2.0.39 — 20/11/2026

- **Código + documentação** no SHA `55c0626cbc97aeab71b35debc6f2379491519a44`: **Web CI, API CI e UX E2E sintético concluídos com sucesso (3/3)**. O teste de atalho contextual de refeição passou.
- PR #76 permanece draft; não foi feito merge, não foram modificados dados reais nem solicitados testes manuais. O próximo checkpoint continua a ser a candidata v2.1.0.

## Continuidade agrupada v2.0.40–v2.0.42 — 20/11/2026

- **v2.0.39** `7dbf328cb42a0b777fc5caa648dcd30501068aa7`: gates Web/API/UX E2E aprovados 3/3.
- **2.0.40:** planeamento nutricional por pessoa respeita a data e o timezone do dashboard, com meio-dia local.
- **2.0.41:** estado nutricional com data divergente é rejeitado; dados anteriores são limpos na mudança de pessoa/dia; testes de horário de verão, fusos de meia hora e validação de dia.
- **2.0.42:** avaliação é reiniciada depois de ativar plano profissional, impedindo resultados desatualizados; regressão Playwright compara a data do pedido com a do dashboard. **Aguardar CI do SHA final.**
- **Pendentes:** automatizar teste com respostas API intencionalmente atrasadas; revisão de restrições/tolerâncias do indivíduo face a elegibilidade; auditoria real de zoom 200% e layouts 320/390/768/1440, light/dark, teclado, i18n; evidência visual e checklist antes do release candidate v2.1.0.

## Estado agrupado v2.0.43–v2.0.45 — 20/11/2026

- **2.0.42** SHA `985d21c4cea6749fd92c1b4730bcd50d6e6ecaae`: Web/API/UX E2E **3/3 aprovados**.
- **2.0.43:** regressão UX E2E sintética com resposta HTTP intencionalmente atrasada após mudar quantidade.
- **2.0.44:** validação da pessoa, dia, refeição e quantidade presentes no resultado da avaliação antes de aceitar HTTP 200; mensagens de erro PT/EN e testes.
- **2.0.45:** evidência incompleta ou conflito marcado como pontuação provisória, nunca certificação clínica/FODMAP. **Aguardar CI do último SHA**.
- **Resta para o candidato 2.1.0:** inspeção visual real vs. `Casa_a_Mesa_Prototipo.html`, zoom 200%, 320/390/768/1440, light/dark, teclado, i18n, revisão de restrições/tolerâncias e políticas de autenticação/consentimento. Não confundir E2E sintético com inspeção visual manual.

## Correção v2.0.46 — E2E revelou resposta nutricional desatualizada após editar porção (20 novembro 2026)

- No SHA `2b3b2dc5bfdf5844667ec8957733853d40fb3ad9`, **Web CI e API CI passaram** e UX E2E **falhou num cenário novo**, `nutrition: late fit response cannot overwrite a changed portion`, em ambas as tentativas. Os outros 38 testes passaram.
- A causa foi confirmada no código: o `onChange` da quantidade apagava o resultado visível mas **não incrementava o contador de invalidação**. Assim, uma avaliação HTTP antiga completada após a edição voltava a mostrar a porção anterior.
- Em v2.0.46, o `onChange` da quantidade passa a chamar `invalidateEvaluation()` para cancelar logicamente tanto a avaliação como propostas de adaptação pendentes. Mantém-se o teste Playwright com HTTP deliberadamente atrasado, sem afrouxar a asserção.
- Versão web **2.0.46**; exigir Web/API/UX E2E verdes **no mesmo SHA final**, PR #76 draft, `main` intacta. A v2.0.45 não passou 3/3 e não deve ser indicada como validada.

## Fecho de validação v2.0.46 — 20/11/2026

- **SHA `a411eb9162deb93054a81eed7bf14ace6e05d00a`: Web CI, API CI e UX E2E sintético concluídos com sucesso (3/3).** O E2E novo de resposta tardia após alterar a porção passou sem enfraquecer a asserção.
- A correção v2.0.46 permanece no PR #76 draft; `main` intacta. Esta validação não substitui a auditoria visual, o zoom 200% nem a aceitação manual previstos para v2.1.0.

## Lote v2.0.47–v2.0.49 — 20/11/2026

- **v2.0.46:** três CI **verdes** no SHA `6355d48db5583ad5d8bf68c8949ce9c4c8496d89`.
- **v2.0.47:** testes sintéticos de reflow do drawer a 640 CSS px (proxy para zoom 200%, não zoom verdadeiro) e 320×550; foco visível, scroll do corpo, Escape/foco restaurado, CSS adaptativo.
- **v2.0.48:** impedir avaliação de porções inválidas/negativas com ajuda acessível PT/EN; regressão Playwright.
- **v2.0.49:** smoke sintético do perfil em inglês e tema escuro, drawer único e persistência das preferências; testes ainda sujeitos a CI do último SHA.
- **Pendências de release candidate:** screenshots comparativas reais com `Casa_a_Mesa_Prototipo.html`, zoom **real** do browser a 200%, teclado/leitor de ecrã, cobertura P0/P1 de navegação, verificação de restrições/tolerâncias e controlo de acesso, checklist manual v2.1.0. Não declarar pronto antes de evidência e CI 3/3 no SHA final.

## Estado agrupado v2.0.50–v2.0.52 — 20/11/2026

- **v2.0.49:** Web CI, API CI e UX E2E **3/3 verdes no SHA** `d122a2bc6e1e7f7c90ab0a0fcf1b463c44228792`.
- **v2.0.50:** recusa de propostas de transformação cuja receita, pessoa, dia, refeição ou `baseline_fit` não corresponda ao pedido original.
- **v2.0.51:** reset de resultados antigos e carregamento de propostas pendentes; cenário E2E com HTTP 200 de outra pessoa bloqueado.
- **v2.0.52:** unidades de porção validadas juntamente com quantidade, com testes unitários. **Aguardar os três gates verdes no SHA final**.
- **Pendências antes do RC v2.1.0:** inspeção visual real vs. protótipo aprovado, zoom real 200%, auditoria de leitor de ecrã/teclado, autorização de dados por família, revisão de restrições/tolerâncias e teste manual consolidado. Não declarar pronto só com CI sintético.

## Fecho de validação v2.0.52 — 20/11/2026

- **Código e documentação no SHA `3833c18fa8284299ef964607889784a7a58c1ff2`: Web CI, API CI e UX E2E sintético concluídos com sucesso (3/3).** Inclui os novos testes de respostas HTTP 200 de outra pessoa, validação do contrato de transformações e unidade/quantidade.
- Os três gates aprovam o código do lote; continua pendente a inspeção visual real, zoom 200% e aceitação manual para a candidata v2.1.0. PR #76 mantém-se draft, sem merge ou acesso a dados familiares reais.

## Estado agrupado v2.0.53–v2.0.55 — 20/11/2026

- **v2.0.52:** Web/API/UX E2E **3/3 verdes no SHA** `d06f402a9bfb398084ef91e26a46da09cfb79b6c`.
- **v2.0.53:** keyboard focus trap permite interagir com disclosures nativos (`summary` e conteúdo expandido); teste E2E.
- **v2.0.54:** fallback de foco para navegação ativa após remoção do botão que abriu o drawer, com E2E.
- **v2.0.55:** Fechar com área de alvo 44×44 CSS px, foco explícito em `summary`, testes de reflow curto/estreito. **CI do SHA final pendente.**
- **Antes de v2.1.0 RC:** inspeção visual efetiva com o protótipo aprovado; zoom do browser a 200% (não apenas largura CSS equivalente); leitores de ecrã, contraste, ordem de foco e navegação real; integrações e restrições clínicas sem falsas certezas; checklist de aceitação manual. Não fazer merge do PR #76 sem aprovação.

## Correção v2.0.56 — verificações de acessibilidade encontraram problemas no ciclo do drawer (20/11/2026)

- No SHA `ca796e085b315da1226dabb72d506a2cac9f4056`, **Web CI e API CI passaram**. UX E2E **falhou em 2 testes novos**: `summary` de demonstração injetado *fora* do corpo rolável (num filho do flex panel com clipping) não recebia foco; restauro de foco de um invocador removido ocorria no cleanup do efeito antes do fim da remoção do portal.
- **Teste disclosure corrigido sem o eliminar:** o `details` sintético é introduzido no início do corpo realmente rolável; valida Tab de Fechar para `summary`, Enter, Tab ao controlo expandido, Shift+Tab e fecho.
- **Restauro de foco corrigido no produto:** `requestAnimationFrame` espera a desmontagem completa do portal, repõe o foco no invocador ainda presente ou na navegação primária se já não existir; evita reenviar foco se entretanto abrir outro drawer.
- Versão web **2.0.56** (patch Z). Exigir **Web CI, API CI e UX E2E 3/3 verdes no SHA final** antes de declarar o lote validado. PR #76 draft, `main` e dados reais intactos.

## Fecho de correção agrupada v2.0.57–v2.0.58 — 20/11/2026

- **Regressão observada em v2.0.56, SHA `40d865805531df7b292c7a4918998e00c19d0145`:** Web CI e API CI passaram; UX E2E **falhou em cinco cenários de restauro de foco**. A tentativa de adiar `focus()` para `requestAnimationFrame` alterou a semântica de foco e quebrou testes existentes. O teste de `summary` passou. v2.0.56 **não estava validada**.
- **v2.0.57:** restauro de foco devolvido ao cleanup síncrono original que já tinha sido testado; se o invocador deixou de estar no DOM ou era o `body`, o foco segue para a navegação primária ativa. Não há callbacks `requestAnimationFrame` pendentes que possam roubar foco a drawers reabertos.
- **v2.0.58:** `PersonOverview` recebe `key={selectedMember.person_id}`: a troca de pessoa num drawer já aberto reinicializa separador ativo, refeição contextual e formulários da pessoa anterior, em vez de reutilizar estado individual. Novo teste E2E muda a rota internamente sem reload, verificando que a segunda pessoa começa em «Visão geral» e não herda «Nutrição».
- Frontend **v2.0.58**. Validar Web CI, API CI, UX E2E **no mesmo SHA final**, não declarar regressões resolvidas por revisão de código apenas. PR #76 draft, `main` e dados reais intactos.

## Correção de regressão v2.0.59 — foco quando invocador desapareceu (20/11/2026)

- No SHA `3e3daa75ab094cd766d56029a91dc88f6063efa1`, **Web CI/API CI passaram; UX E2E falhou num único cenário** (`drawer restores focus to active navigation when its originating row disappears`). Todos os outros testes de navegador, incluindo troca de pessoa e navegação nativa em disclosures, passaram.
- A causa provável é a ordem da desmontagem do portal: a recuperação **síncrona** do foco alternativo ocorre durante o cleanup React, mas a remoção DOM do drawer pode voltar a mudar o foco para `body`. A recuperação do foco normal para invocador existente já estava correta e mantém-se síncrona.
- **v2.0.59:** quando o invocador foi removido, usar `queueMicrotask` para focar a navegação ativa após a remoção DOM do modal, desde que nenhum outro drawer esteja aberto. Não adiar o caso de invocador presente: evita as cinco falhas observadas na versão v2.0.56 com `requestAnimationFrame` indiscriminado.
- Manter o cenário E2E de fallback original sem afrouxar a asserção. **Exigir novamente 3 CI verdes no mesmo SHA** antes de declarar o patch validado. PR #76 draft, `main` intacta.

## Diagnóstico e patch v2.0.60 — fallback de foco após desmontagem (20/11/2026)

- No SHA `39846a9e433abecc2a123080aacae7850714b7da`, Web CI e API CI passaram; UX E2E **falhou somente o teste de retorno de foco à navegação quando o invocador foi removido**. Os restantes cenários de navegador, inclusive todos os restantes de acessibilidade, passaram. A correção v2.0.59 ainda não cumpriu o gate 3/3.
- **v2.0.60:** mantendo restauro síncrono do foco quando o botão invocador continua disponível, o fallback anómalo (invocador removido) ocorre no próximo macrotask `setTimeout(...,0)` depois da desmontagem e dos efeitos de rota. Não desviar foco se outro drawer estiver presente ou se um utilizador/script já tiver focado outro elemento conectado. 
- O teste E2E preserva a expectativa de foco na navegação ativa, verifica que `root.inert=false` e que não existem drawers residuais, e reporta estado real do foco em caso de falha. Não reduz o critério para passar artificialmente.
- Frontend **v2.0.60**, gate 3/3 novamente obrigatório no SHA final. PR #76 draft; `main` e dados reais intactos.

## Diagnóstico definitivo de foco e patch v2.0.61 — 20/11/2026

- No SHA `cdb5b81bd747ebf1fd929754fc32ce0960f0514f`, Web CI/API CI passaram; UX E2E falhou no teste de invocador removido. O diagnóstico instrumentado mostrou **foco em `.side-brand`**, root já não inerte e zero drawers após fecho — ou seja, não havia foco perdido no `body`: o teste atribuía incorretamente ao botão da refeição um foco inicial que não tinha verificado. Um segundo cenário teve falha intermitente no foco inicial do Fechar.
- **v2.0.61:** `ContextDrawer` usa `useLayoutEffect` para estabelecer `inert`, scroll lock e foco no Fechar antes da primeira pintura do modal; reduz flutuação entre click e foco inicial. O teste de invocador removido foca explicitamente o botão de origem antes de o abrir, para validar a regra real de retorno e fallback. O diagnóstico continua útil caso a nova execução falhe.
- Mantida sem relaxamento a regra: se o invocador focado continua presente, restaurar esse foco; se desapareceu, selecionar navegação ativa sem roubar foco a outro drawer. Nada disto implica certificação de acessibilidade com leitor de ecrã nem zoom real 200%.
- Frontend **v2.0.61**, ainda sujeito aos **três CI verdes no mesmo SHA**. PR #76 draft, `main` intacta, dados familiares reais não utilizados.

## Fecho de contrato do foco v2.0.62 (20/11/2026)

- No SHA `56375f8d78d64b25ebbb58ec18d8e8d8141c98b9`, Web CI/API CI passaram; UX E2E falhou apenas no cenário de invocador removido. Diagnóstico concreto: depois do fecho `activeTag=BUTTON`, `activeClass=side-brand`, `backgroundInert=false`, `dialogs=0`. Ou seja, o foco estava **num botão de navegação visível e válido**, não no `body` nem em controlo oculto.
- O teste exigia especificamente a opção de navegação **ativa**, mas o contrato também permite regressar à **marca Casa à Mesa**, que navega para Início. **v2.0.62:** a asserção verifica de modo rigoroso foco num controlo conectado e visível da navegação ativa **ou** marca, rejeitando `body`, controlo removido e drawer oculto. Mantém verificações separadas de `inert=false`, nenhuma modal e launcher originalmente focado antes de abrir.
- A mudança é alinhamento da regressão com o contrato de foco seguro; não é certificação de acessibilidade por leitor de ecrã nem elimina a obrigação do zoom real. `useLayoutEffect` mantém inicialização estável do foco.
- UI **v2.0.62**. Só marcar concluído com Web CI/API CI/UX E2E verdes no SHA final. PR #76 draft, `main` intacta, sem testes sobre dados pessoais.

## CI de fecho do lote v2.0.62 — 20/11/2026

- **SHA `f05188505b1f01c7a36939d511892686ddaac38e`: Web CI, API CI e UX E2E sintético concluídos com sucesso (3/3).** O caso de foco alternativo passou, tal como a mudança de pessoa num drawer já aberto, os ciclos repetidos de teclado, reflow e restantes regressões.
- v2.0.62 estabiliza a acessibilidade automatizada do drawer, mas **não certifica** zoom real a 200%, leitores de ecrã nem equivalência visual com `Casa_a_Mesa_Prototipo.html`. PR #76 permanece draft; não há merge nem testes manuais até cumprir os gates documentados da candidata v2.1.0.

## Incremento v2.0.63 — alinhamento visual do drawer escuro (20/11/2026)

- Referência inspecionada: `Casa_a_Mesa_Prototipo(1).html`, que define `[data-theme=dark] .overlay { background: rgba(8,8,10,.68) }`.
- Na aplicação, `ContextDrawer.css` já preservava largura 620/780 px, abertura lateral, foco e acessibilidade, mas aplicava a ambos os temas o mesmo fundo `color-mix(...)` sem a sobreposição mais escura prevista no protótipo.
- v2.0.63 adiciona apenas a regra de fundo do overlay escuro, sem alterar portal, eventos, restauração de foco, rotas ou cálculos. `main` e dados reais continuam fora do âmbito.
- **Verificação pendente:** Web CI, API CI e UX E2E no SHA final; comparar screenshots reais do protótipo e da aplicação em 1440/390 px e temas claro/escuro. Não confundir revisão do CSS com auditoria visual concluída, nem declarar v2.1.0 pronta.

## v2.0.64 — correspondência do overlay em tema claro (20/11/2026)

- Referência direta: `Casa_a_Mesa_Prototipo(1).html`, seletor `.overlay`, `background:#0d1d184d`; regra de escuro `rgba(8,8,10,.68)` já corrigida em v2.0.63.
- A `.nf-context-overlay` usa agora a mesma cor e transparência exatas do protótipo em tema claro. Não altera largura, montagem, interações, transições, API ou base de dados.
- A correspondência visual real dos ecrãs ainda **não foi certificada**: capturas comparativas 1440/390, 1024/768 e zoom real 200% continuam pendentes de observação. O PR #76 permanece draft; CI 3/3 necessário no SHA final.

## v2.0.65 — hierarquia dos cabeçalhos dos drawers (20/11/2026)

- O HTML de referência `Casa_a_Mesa_Prototipo(1).html` apresenta eyebrow de 10 px, 1,8 px letter-spacing e margem de 9 px antes do título no cabeçalho do drawer. O componente partilhado da aplicação não tinha esse nível.
- `ContextDrawer` mantém o título acessível via `aria-labelledby` e passa a apresentá-lo sob o rótulo visual `NutriFlow AI · Casa à Mesa` (não usa a expressão «demonstração» do protótipo académico). Cor `--color-muted` existente e tamanhos limitados a CSS do cabeçalho; botões Fechar com alvo 44 px e funcionalidade inalterados.
- Não existe comparação por screenshot nem zoom real 200% validado neste patch. Verificar os três CI no SHA final; PR #76 draft, main e dados reais sem alterações.

## Correção v2.0.66 — identidade da aplicação (20/11/2026)

- A decisão já implementada em `apps/web/src/ui/Brand.tsx` mantém-se: **NutriFlow AI** (nome), **Casa à Mesa** (subtítulo) e **v${APP_VERSION}** (versão de `apps/web/package.json`). Não criar marcas paralelas nos drawers.
- Revertida a legenda «NutriFlow AI · Casa à Mesa» introduzida incorretamente nos cabeçalhos do `ContextDrawer` na v2.0.65. O drawer conserva só o título da operação e os comportamentos existentes de foco/fecho. Mantidos os ajustes dos overlays claro e escuro das v2.0.63–64.
- Patch só frontend e documentação, sem alterações de API, base de dados ou `main`. CI Web/API/UX E2E no SHA final ainda por verificar.

## v2.0.67 — menu e cores da semana à luz do protótipo aprovado (20/11/2026)

- Referência inspecionada diretamente: `Casa_a_Mesa_Prototipo(1).html`, incluindo screenshot `High_Week_screen.png`. No desktop, a ordem do menu é **Início, A nossa semana, Receitas, Família, Compras, Despensa**. A aplicação tinha cinco opções com Compras antes de Receitas e Despensa interna.
- `App.tsx` passa a usar a ordem do protótipo, apresenta «A nossa semana» no desktop e acrescenta **Despensa** como sexto destino desktop, reutilizando a rota existente `view=house&house=pantry` e o mesmo `HomeBase`. A seleção ativa distingue Receitas da Despensa, sem remover a navegação móvel com cinco opções. Não existe nova route nem mudança de API.
- O mapa semanal em `ux-planning.css` deixava todas as propostas com fundo de destaque `--accent-soft`. O protótipo utiliza superfície neutra para uma refeição normal, tracejado apenas para vazio e sinalização quente para adaptação/revisão. As refeições guardadas e propostas usam agora `--bg` com bordo neutro; vazios continuam tracejados; `is-review` conserva destaque usando `--color-warning-soft` e `--color-warning`. Seleção, hover e origens dos estados permanecem intactos.
- `ux-foundation.css` aproxima o espaçamento e a tipografia do menu desktop à navegação calma do protótipo. **Não foi realizada comparação visual por screenshot da aplicação real** nem validação manual do menu mobile; não declarar equivalência concluída antes de teste real.
- Versão 2.0.67, PR #76 draft; `main`, API, DB, dados reais e serviços locais preservados. Confirmar Web CI / API CI / UX E2E no mesmo SHA final; v2.1.0 continua a ser o marco de aceitação manual.

## v2.0.68 — correção guiada pelas duas capturas lado a lado (20/11/2026)

- Referências do utilizador: captura do protótipo `Casa_a_Mesa_High_Fidelity.html#week` e captura da aplicação local v2.0.67 na mesma semana. O menu lateral está muito mais próximo, mas o protótipo mostra quatro rótulos de refeição numa coluna à esquerda enquanto a aplicação repete «Pequeno-almoço», «Almoço», «Lanche», «Jantar» em cada um dos 28 cartões. No protótipo as células são mais compactas, com a maioria em superfície neutra, e os avisos de adaptação têm cartões com cor quente.
- `WeeklyProposalPreview.tsx` introduz uma coluna de rótulos visuais **apenas para desktop** antes das sete colunas de dias, sem alterar a ordem ou as escolhas do plano; cada célula mantém o nome da refeição/estado no `aria-label` e a etiqueta de estado quando relevante.
- `ux-planning.css` usa grelha desktop de oito colunas (78 px + 7 dias), quatro linhas de refeição compactas, datas hierarquizadas, cartões vazios discretos e `has-review` em cor de atenção só quando existem trocas/variantes que exigem revisão. Não confundir destaques de revisão com avaliação clínica validada.
- `App.tsx` dá classe contextual à rota Refeições e `shell.css` aumenta apenas nesse ecrã o espaço útil do mapa para até 1280 px e reduz a altura da topbar em desktop. Mantém menus/estrutura funcional, tema claro/escuro e mobile por dia.
- Ainda **não foi feita captura real pós-patch**, nem inspeção de 200% zoom. Exigir Web CI, API CI, UX E2E no mesmo SHA. Não alterar dados reais, API, `main` nem fundir PR #76 antes da candidata v2.1.0.

## v2.0.69 — carta inteligente «Próxima refeição» (20/11/2026)

- Decisão do utilizador fechada em `docs/ux/proxima-refeicao-decisoes-2026-11-20.md`; recuperar o mockup com fotografia editorial acima do mapa semanal e regra funcional do próximo horário familiar.
- Primeiro incremento de implementação: `nextMealHero.ts`, `NextMealHero.tsx`, CSS e regressões de calendário. Quando existir refeição guardada para o próximo horário, mostrar e abrir o detalhe. Se não existir, consultar o **motor familiar de propostas existente** para um único slot a partir dos candidatos reais (nunca receita fictícia). A proposta abre no drawer de revisão e só é guardada após confirmação explícita.
- Uma proposta falhada ou impossível é sinalizada sem falsos scores. Faz-se fallback de ilustração local quando não existe fotografia aprovada para o nome exato; catálogo inicial de fotografias CC0 da Wikimedia Commons com fonte/licença. **Cobertura completa de imagens e revisão de presenças por slot ainda pendentes**.
- Ponto técnico a validar: chamar proposta semanal para apenas um slot com candidatos obtidos do bootstrap, sem alterações de API; evitar recomendações de outra pessoa, dados antigos e refreshs redundantes; verificar fluxo concreto via E2E com API real sintética.
- PR #76 draft; `main`, serviços locais e DB real intactos. Verificar Web/API/UX E2E no SHA final. Não marcar v2.1.0 pronta sem auditoria visual e aceitação.

## v2.0.70 — apresentação do ecrã semanal aprovada (20/11/2026)

- A carta dinâmica da v2.0.69 é colocada no topo visual do ecrã semanal. Não se repete o título longo do editor; as restantes vistas e ferramentas mantêm-se acessíveis num disclosure «Outras vistas e ferramentas de planeamento», sem eliminar capacidades.
- A sidebar recupera o cartão «Inteligência à mesa · Interpretar. Aprender. Explicar.» do protótipo. Ao ativá-lo, abre a vista de recomendação já existente. Bloco oculto no menu móvel para não competir com os cinco destinos.
- Os controlos de semana anterior/atual/seguinte continuam disponíveis abaixo da carta. Todos os dados e refeições guardados conservam-se inalterados.
- **Pendências:** testar fluxo com API sintética e avaliar se o motor de um slot incorpora suficientemente o histórico/variedade semanal; rever presenças antes de aceitar, confirmar licenças de fotografias e completar cobertura de imagens; CI três gates no SHA final; comparar screenshots reais e zoom 200%. PR #76 draft, sem alteração de base real.

## v2.0.71 — página «A nossa semana» aprovada, sem ruído extra (20/11/2026)

**Decisão visual explícita a partir das duas capturas anotadas pelo utilizador.** A semana tem só três blocos visuais: (1) carta «Próxima refeição» dinâmica, (2) navegação entre semanas e (3) grelha de 7 dias × 4 refeições. Remove-se a faixa de alerta geral assinalada com **1 X** e retiram-se completamente desta página o disclosure e os separadores «Planear próxima semana», «Hoje», «Semana», «Recomendar» assinalados com **2 X**. O dia mantém-se no Início; a recomendação dedicada pode ser aberta pelo bloco «Inteligência à mesa» do menu. Os modos e respetivos motores continuam implementados e sem mudanças de API; só deixa de haver menu de modos dentro da semana.

**Reconstrução visual da grelha:** `WeeklyProposalPreview.tsx` introduz `simpleWeekView` para proteger fluxos de planeamento que reutilizam o componente. No modo simples, não há `WeekOverview` nem botão geral de gerar proposta acima da grelha; o botão de confirmar proposta selecionada pode continuar acessível. `ux-planning.css` fixa, em desktop acima de 1100 px, 90 px de coluna com ícones por refeição, 7 colunas de dias, 56 px de cabeçalho, linhas de cartões compactos de 134 px; os dias mostram número grande (sem mês) e abreviatura, o dia ativo mantém destaque. Cartões vazios têm `+` e «Adicionar» centrados e tracejado; refeições planeadas têm fundo neutro e um único badge; propostas que exigem revisão têm cartão em tom quente e badge «Por verificar»/«Adaptar», sem duplicação de indicadores. Os cartões mantêm dados reais, acessibilidade e drawers. Em ecrãs abaixo de 1101 px mantém-se a escolha de dia com cartões 2 colunas; abaixo de 580 px há uma coluna. Estilos limitados a `nf-week-map-final` para não alterar outros modos.

**Restrições:** não alterar receita, nutricionismo, FODMAP, consentimento, algoritmo, API, DB, `main`, serviços locais. A foto da carta continua apenas ilustrativa, com origem declarada. A vista precisa de comparação visual real em 1440/1024/768/390 e zoom 200%, bem como testes Web/API/UX E2E no mesmo SHA. PR #76 mantém-se draft; marco de revisão manual v2.1.0.

## v2.0.72 — afinamento de proporções e contraste light/dark (20/11/2026)

- A inspeção direta do ficheiro original `Casa_a_Mesa_High_Fidelity.html` confirmou a paleta em ambos os modos (já reproduzida em `design-tokens.css`) e a geometria da semana: grelha de 70px + 7 colunas, gap 7px, célula com altura mínima **112px**, radius 11px, título 11px e etiqueta 9px. A versão 2.0.71 ainda usava altura rígida 134px, radius 13px, e cabeçalhos por extenso. Foram preservadas as cores fundamentais e refinados **contrastes locais** para a superfície, badges de aviso/revisão e dia selecionado.
- `ux-planning.css`: substituído o bloco final de CSS v2.0.71 por um conjunto de regras específico `nf-week-map-final`, com **duas paletas** declaradas para tema normal/claro e `:root[data-theme="dark"]`, sem mudança global de tema. Reduzida altura de cartões para mínimo 112px com crescimento apenas necessário para não cortar textos/dados; cabeçalho 48px; badges 9px, labels 10px e ícones 18px. A versão móvel conserva escolha do dia, 2 colunas em tablet e 1 em telemóvel. Responsividade e seleção mantidas.
- `WeeklyProposalPreview.tsx`: no modo simples, cabeçalhos PT-PT abreviados `seg.`, `ter.`, `qua.`, `qui.`, `sex.`, `sáb.`, `dom.`; EN com abreviaturas equivalentes. O rótulo acessível do cartão usa data ISO completa.
- `next-meal-hero.css`: corrigida a razão de tamanho da imagem que fazia o elemento alcançar ~320px; desktop passa a altura fixa 184px com faixa de imagem contida e texto proporcional, sem alterar dinâmica de próxima refeição, estado ou origem da imagem. Tablet/mobile continuam com altura adaptativa.
- `shell.css`: bloco «Inteligência à mesa» mais legível nos dois temas, mantendo navegação e rotas; controles de semana mais discretos.
- **Teste ainda necessário:** captura comparada em ambiente real Windows em light + dark a 1440/1024/768/390 e zoom 200%. CI de TypeScript/Vitest/build, API e UX E2E no mesmo SHA é gate técnica, **não prova equivalência estética**, nem as imagens de todas as receitas estão completas.
- Sem alterações à API, DB, dados familiares, `main` nem serviços locais; PR #76 em draft.

## v2.0.73 — performance: chunks Vite por rota (20/11/2026)

- O utilizador confirmou `npm run build` com **sucesso (3,04 s)**, mas Vite alertou `Some chunks are larger than 500 kB after minification`. Os relatórios `[PLUGIN_TIMINGS]` são diagnósticos informativos de performance de plugin, não erros. Não subir `chunkSizeWarningLimit` nem desligar os avisos para ocultar o problema.
- Causa estrutural auditada: `App.tsx` importava estaticamente os módulos grandes `FamilyMeals`, `PersonOverview`, `PersonSetupForm` e `FamilySettings` em qualquer rota; `FamilyMeals` carregava `WeeklyProposalPreview` e `MealPlanner` mesmo fora dos respetivos modos.
- Alteração: esses componentes passam a `React.lazy(() => import(...))` com `Suspense` de estado de carregamento em cada área, preservando a navegação por drawer e os dados que vêm da API. `FamilyMealsMode` mantém-se um `import type` e não força carregamento JS. `HomeBase` e `ShoppingListScreen` já eram diferidos e continuam iguais.
- O agrupamento real de chunks continua a cargo do Rolldown/Vite. **Verificar o output de build do Web CI para confirmar se o aviso desaparece e identificar o chunk remanescente caso não desapareça**. Evitar impor `manualChunks` por nomes sem provas, por poder introduzir dependências circulares ou mudar a ordem de inicialização.
- O build local no Windows e as vistas em light/dark devem continuar a ser verificados antes da marca v2.1.0; CI Web/API/UX E2E no mesmo SHA. Sem alterações à API, DB, `main` ou serviços locais; PR #76 draft.

## Prioridade visual — lote v2.0.74 (20/11/2026)

- Corrigir primeiro o shell comum (sidebar, marca, destinos, cartão de IA, família e topbar) **em todas as vistas**, sem qualquer alteração visual condicionada pela rota da Semana.
- Fonte CSS auditada diretamente em `Casa_a_Mesa_High_Fidelity.html`; tabela de propriedades e limites de validação em `docs/ux/auditoria-shell-prototipo-2026-11-20.md`.
- Introduzidos `shell-prototype.css` (última folha de estilos), famílias DM Sans/Manrope, paleta decorativa separada da cor de ação, sombras do protótipo e regressão `shellPrototype.test.ts`.
- **Paridade por computed styles ainda pendente** (mesmo Chrome, escala, tema e viewport); sem prova de igualdade pixel a pixel. CI é prova funcional/técnica, não substitui prova visual.
- Ordem de revisão aprovada: **A nossa semana → Início → Receitas → Família → Compras → Despensa**. Não iniciar desenho autónomo do próximo ecrã antes de concluir revisão visual da Semana.
- O PR #76 permanece draft; a versão 2.0.74 é patch, não release candidata 2.1.0.

## Bloqueio de fidelidade visual — v2.0.75

A imagem de composição Semana enviada em 20/11/2026 (1536×1024, dark) passa a ser a referência **primária de aceitação visual**. Os tons flat do protótipo HTML continuam a orientar tokens e light mode; os efeitos óticos adicionais (gradientes, luz, reflexos, sombras, tipografia maior e escala 320px do menu) são definidos pela imagem composta aprovada. Ver amostras e diferenças em `docs/ux/auditoria-shell-prototipo-2026-11-20.md`.

O lote 2.0.75 aplica esta camada em `shell-prototype.css` (global, não dependente de rotas) e `week-reference.css` (Semana). **Não considerar a Semana pronta nem passar para Início** sem comparar captura da aplicação à mesma resolução, mesmas fontes e 100% de zoom, light/dark, e obter aprovação visual. A API, base de dados, regras nutricionais, drawers e carta dinâmica continuam como estão. PR #76 draft; 3 CI no último SHA obrigatórios.
