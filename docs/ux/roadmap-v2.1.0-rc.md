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

## v2.0.87 — primeiro lote de uniformização após aprovação da Semana (21/11/2026)

O utilizador aprovou visualmente a Semana v2.0.86 no Chrome com fotografia de frango no hero e autorizou avançar para os **outros menus/ecrãs**, recuperando depois a lista de pendentes do roadmap. A Semana aprovada passa a servir de referência de **densidade e acabamentos**, sem alterar os seus cartões nem os seus dados.

- Criado `apps/web/src/screen-reference.css` carregado depois do CSS legado: tokens e tipografia partilhados de cabeçalhos, cartões e superfícies, com estilos aplicados a `nf-home`, `people-screen`, `home-base`, `shopping-screen` e `settings-screen` para reduzir divergências entre rotas.
- **Início (primeiro ecrã a uniformizar)**: hero com superfície editorial carvão/âmbar em dark e superfície suave em light, dimensão mais compacta, títulos DM Sans/Manrope, botões com contorno de ação, cartões dos quatro momentos menos altos; mantém a ilustração/funções originais e não inventa recomendações. Painéis familiares e atalhos permanecem no DOM com as mesmas ações. **Não foi declarada igualdade pixel a pixel** nem concluída revisão manual do Início.
- **Restantes menus**: primeiro passe transversal de tipografia, raio, cor de borda e sombra dos cartões em Receitas, Família, Compras e Despensa sem alterar formularios, filtros, lógica, navegação ou drawers. Uma revisão ecrã a ecrã da composição específica **continua pendente**, na ordem Início → Receitas → Família → Compras → Despensa.
- `shell-visual-parity.spec.ts`: adicionada captura de Início em light e dark numa base sintética, assertivas de estilo e existência de contentores para outras rotas. Web/API/E2E devem passar no SHA final; comparar os novos screenshots antes de pedir revisão humana.

### Pendentes funcionais recuperados do roadmap (sem os marcar como concluídos)

1. **UX visual/acessibilidade:** comparação lado a lado com o protótipo dos restantes 5 ecrãs, light/dark, larguras 1440/1024/768/390, zoom 200%, navegação por teclado, foco e drawers.
2. **Presenças:** padrões por dia/slot, exceções e convidados; não equiparar «por confirmar» a «ausente»; revalidar elegibilidade quando participantes mudam.
3. **Refeição/receitas/adaptações:** fluxo completo de rever receita adaptada no drawer, reabrir rascunhos, confirmação explícita, não modificar originais ou compras antes de aceitar; avaliações familiares 1–5 separadas de segurança nutricional.
4. **Nutrição:** comparar porção real à orientação profissional ativa com fonte/validade, manter incógnitas explícitas, demonstrar FODMAP sem validação clínica indevida e tratamento de respostas API fora de contexto.
5. **Despensa/compras:** consistência de stock, validade e unidades; diferenciação comprado/recebido, recebimentos parciais, regeneração e eliminação de necessidades após adaptações.
6. **Idiomas, estabilidade, privacidade e lançamento:** PT/EN, offline/erro rede, concorrência, no data leakage, revisão dos casos da checklist `docs/ux/aceitacao-manual-v2.1.0.md`; apenas depois marcar RC 2.1.0 pronta e solicitar autorização para merge.

PR #76 mantém-se draft, branch existente; sem intervenções na API, DB real, serviços Windows, processos locais ou main.

## v2.0.88 — cinco imagens de referência aprovadas, preservadas e início da implementação fiel (21/11/2026)

O utilizador aprovou **sem alterações** as cinco imagens high-fidelity geradas nesta conversa para Início, Receitas, Família, Compras e Despensa. A decisão é mais forte do que uma direção estética: **o objetivo é reproduzir a estrutura, hierarquia, fotografias, cores, fontes, proporções, cartões, sombras, brilhos e densidade desses cinco PNG**, com toda a página principal visível no viewport desktop sempre que a quantidade real de dados o permita. Não substituir essas imagens por novas propostas ou por um layout aproximado.

As **cinco imagens PNG originais** (1672 × 941 px) foram preservadas em 21/11/2026 numa pasta persistente da Biblioteca do utilizador: `NutriFlow AI v2 / UX References`, ficheiros `inicio.png`, `receitas.png`, `familia.png`, `compras.png`, `despensa.png`. Foi gerado o pacote integral `nutriflow_ux_references_v1.zip` na conversa, contendo a estrutura `docs/ux/references/*.png` e manifesto de SHA-256. No GitHub, `docs/ux/references/manifest.json` e `README.md` fixam os hashes e critérios de aceitação. **Limitação técnica explícita:** o conector GitHub disponível aqui escreve texto UTF-8 mas não aceita os ficheiros PNG binários como fonte; estes ainda não constam do Git. O ZIP permite inseri-los no checkout mantendo os hashes idênticos. Não afirmar que os PNG já foram comitados enquanto isso não acontecer.

Implementação desta ronda:
- `FamilyHome.tsx`: fotografia do próximo prato real via `resolveMealHeroImage` (o mesmo catálogo verificado que alimenta a Semana); fallback neutro quando não existe imagem segura. As decisões da próxima refeição e os dados familiares não mudaram.
- `RecipeCatalogue.tsx`: fotografias curadas por nome de receita dentro de cartões, com `onError` e fallback para icon, sem dar aparência de composição nutricional verificada.
- `screen-reference.css`: compactação do Início com hierarquia editorial e sem reduzir funcionalidades. Layout de catálogo de Receitas em 4 colunas no desktop, 3 no tablet, 2 no mobile; fotografias com `object-fit:cover`, cartões alinhados e informação real de ingredientes. Compras e Despensa com espaçamentos de listas e resumos refinados. Mantida a Semana aprovada sem alterações.
- A equivalência visual exata do Início, Receitas, Família, Compras e Despensa **ainda não está demonstrada nem concluída**: continuar por lotes com screenshot em dark, light, 100% e 200%, sem scroll desnecessário e sem ocultar dados para falsificar o fit.
- PR #76 mantém-se draft; CI em todos os lotes, sem alterações de API, base de dados real ou processos Windows.

### Inspeção visual das capturas Chromium v2.0.88 — 21/11/2026

Commit `804e1e52ca225ec8eee9ed521f92c6acbecddf02`: **Web CI + API CI + UX E2E synthetic 3/3 success**. Artefacto de 16 capturas `screen-visual-ef000a5a4c28cedfc973489694de1670bc1a621c` descarregado e comparado com as cinco referências aprovadas.

- **Início:** refatorado para hero full-width com imagem à esquerda, cartões do dia à esquerda, painel familiar à direita, atalhos e semanas guardadas em baixo; CSS com medição por viewport. A nova composição aproxima-se da referência mas ainda tem diferenças importantes: falta o painel de progresso nutricional real, a densidade/imagem dos quatro pratos e atalhos em quatro mosaicos. Não mostrar os 72% ou valores inventados do mock.
- **Receitas:** cartões com fotografias curadas e grelha 4/3/2 colunas implementados, mas o conjunto sintético E2E não contém receitas, por isso o PNG mostra o estado vazio. Ainda faltam um bloco de receita em destaque e painel de sugestões com dados reais.
- **Família:** grelha compacta de cartões de membros em vez das antigas linhas e preservação dos drawers. Falta a área comparativa de restrições/preferências baseada em dados reais.
- **Compras e Despensa:** hierarquia de superfícies e densidade refinadas. Capturas E2E sintéticas vazias não validam a fidelidade dos estados preenchidos nem as informações de stock. Continuam a faltar as secções laterais e resumos específicos dos desenhos, baseados em dados reais.
- O shell comum e a **Semana aprovada** passaram a regressão. Próximos lotes devem ser guiados pelos PNG originais e não por analogias visuais. Critério de fit: página principal inteira no viewport desktop se o conteúdo permitir, scroll próprio em listas extensas. A equivalência pixel a pixel **não está aprovada**.

**Estado dos ficheiros de referência:** as cinco imagens PNG e o ZIP original estão persistidos na Biblioteca do utilizador, `NutriFlow AI v2 / UX References`; no GitHub estão os hashes/manifesto e instruções de importação binária. Não esquecer que os PNG não estão ainda dentro da árvore Git até importação explícita do ZIP pelo utilizador ou disponibilização de escrita binária.

## v2.0.91 — lote adicional antes de teste manual: Início fit + dados reais (21/11/2026)

O utilizador voltou a indicar que o **Início ainda não cabe no ecrã do seu Chrome** e que os cinco ecrãs ainda estão longe dos desenhos de referência aprovados. Este lote responde à prioridade de caber na altura real de viewport, sem solicitar teste manual antes de estabilizar o CI.

### Mudanças concretas

- `FamilyHome.tsx`: cartões das quatro refeições apresentam fotografia do prato somente quando `resolveMealHeroImage` dispõe de imagem validada para o nome real, com fallback discreto. A secção inferior passa a ter **quatro ações reais**: planear semana, ver receitas, lista de compras e adaptar o plano (esta última abre o planeamento existente). Não se fabricam receitas, estados ou classificações nutricionais.
- `FamilyHome.tsx`: o painel lateral da família passou a integrar um pequeno resumo com energia consumida por membro quando existem estados nutricionais no dashboard; caso contrário indica que faltam dados. **Não são inventadas metas diárias, percentagens de adesão, diagnósticos ou valores profissionais**. Mantêm-se todos os membros e acessos aos seus perfis.
- `screen-reference.css`: compactação responsiva adicional para ecrãs desktop de altura curta (até 830 e até 700 CSS px), com escalonamento de hero, títulos e margens, e scroll **apenas dentro do painel familiar** quando existem muitos membros. Em mobile o layout continua a crescer naturalmente. O compromisso é não esconder ações ou membros para satisfazer fit.
- `PantryScreen.tsx`: quatro indicadores derivados dos lotes reais — disponíveis, validade a rever, sem validade e total registado. `ShoppingListScreen.tsx`: quarta métrica, receções parciais reais, mantendo a distinção comprado/recebido e as operações existentes.
- `e2e/shell-visual-parity.spec.ts`: novo teste sintético de 1280 × 700 px com quatro membros. Mede a posição final do conteúdo relativamente à altura da janela, verifica scroll interno da família e não-overflow horizontal. Novas assertivas de quatro cartões no resumo de compras e despensa.

### Restrições ainda aplicáveis

- Fotos e dados dos PNG aprovados são **mockup**, não dados a injetar na aplicação. A semana v2.0.86 mantém-se intocada; PR #76 draft; sem DB real/backend local/serviços.
- A equivalência final com `inicio.png`, `receitas.png`, `familia.png`, `compras.png` e `despensa.png` ainda precisa de revisão visual nos estados preenchidos.
- Critério de fit não substitui testes a 200% zoom, 390/768/1024/1440 e diferentes alturas. Em páginas com listas extensas, o scroll dentro da lista é aceitável, não a perda de dados.

## v2.0.92 — segunda correção de densidade do Início (21/11/2026)

O teste sintético da v2.0.91 (1280 × 700 CSS px, quatro membros) passou e a captura mostrou que **já não era preciso scroll**, mas o Início estava pequeno demais e havia excesso de espaço vazio no fundo; o painel lateral só mostrava aproximadamente um membro antes de fazer scroll. Critério do utilizador: ocupar bem o ecrã mantendo a página inteira visível.

Correção em `screen-reference.css`: a grelha principal passa a utilizar `height:min(775px, calc(100dvh - 94px))` com linhas flexíveis e uma linha central `minmax(0,1fr)`, ampliando os cartões do dia e o painel familiar segundo a altura efetiva. Hero e ações rápidas mantêm-se acessíveis no mesmo viewport. A família pode fazer scroll interno quando o número de membros é elevado; o teste E2E exige **pelo menos três membros visíveis**, sem scroll de página, a 1280 × 700. Para alturas pequenas e mobile mantém-se fallback responsivo. O botão «Adaptar plano» encaminha agora para `mode=recommend` através da navegação existente, não apenas para o mapa semanal.

O hero do Início exibe atribuição discreta sobre a fotografia licenciada (autor/licença/link) sem aumentar a altura. Não se alteraram a Semana aprovada, o backend ou a base de dados real.

A versão está pronta para avaliação apenas depois de Web CI, API CI e UX E2E no **mesmo SHA final**, com captura da nova geometria. Continuam pendentes equivalência visual exata dos cinco PNG e estados preenchidos dos restantes ecrãs.


## Continuidade — 21/11/2026, navegação de dia na Semana (commit e67a0ac64159)

- Corrigida a visibilidade do dia selecionado na barra horizontal de escolha de dia em `WeeklyProposalPreview.tsx`. O mapa já tinha seleção de hoje quando a semana contém a data local da família e não existe seleção explícita; o efeito anterior deslocava apenas a grelha compacta, deixando o seletor horizontal na posição inicial.
- A barra de dias passa a centrar a data selecionada quando tem overflow. A navegação manual e a seleção explícita por URL continuam prioritárias; não há foco de teclado forçado, abertura de drawer, mudança de URL nem escrita de dados.
- Validação local em Chrome/Windows ainda pendente; Web CI, API CI, Deployment Script CI e UX E2E devem ser conferidos no SHA exato. Não declarar o erro `Cannot safely adopt process on port 5173` resolvido: a identidade/posse do processo local requer diagnóstico no Windows. Usar `./deploy.ps1 -Diagnose` (PowerShell `.\\deploy.ps1 -Diagnose`) e não terminar PID desconhecido.
- Continuam pendentes: correspondência visual exata dos cinco ecrãs; dados de refeições passadas no gráfico com origem explícita; imagens de receitas em falta; política idempotente para receitas familiares e correção local de adoção do Vite. PR #76 continua draft e não foi feito merge.


## v2.0.94 — Revisão da captura Windows de 21/11/2026 às 23:50

Na captura do Chrome, o dia **sábado 21** já está selecionado, mas o calendário continua abaixo da dobra do viewport. A proposta automática de pequeno-almoço do dia 22/11 não encontra opção elegível comum devido a restrições/regras; esse resultado não é corrigido fabricando uma receita nem ignorando regras obrigatórias.

- `WeeklyProposalPreview.tsx`: quando não há plano selecionável no modo Semana, os motivos por slot permanecem acessíveis num painel `details/summary` fechado inicialmente; no planeador completo continua a apresentação original expandida.
- `week-reference.css`: painel compacto, contraste e foco visível para teclado.
- Commits `bd7e679` e `283420b`. A alteração anterior `e67a0ac` centra o dia selecionado no picker horizontal quando existe overflow.
- Pendente: verificar CI completo, medição visual do fit da grelha de 4 refeições no viewport real e a causa de rejeição do pequeno-almoço de domingo no motor, com dados sintéticos e sem relaxar restrições de segurança nutricional. Não considerar o planeamento automático resolvido.


## v2.0.95 — pequeno-almoço e substituição do leite (21/11/2026)

A investigação do código revelou **11 receitas** comuns de pequeno-almoço, incluindo 7 com leite meio-gordo. A fonte `development_plant_milk_seed.py` já define alternativas `plant-milk:lactose-free` e `plant-milk:rice`, com transformação automática, e alternativas aveia/arroz-coco registadas mas não automáticas. Os valores nutricionais destes substitutos são estimativas de desenvolvimento, não rótulos reais verificados nem prova clínica FODMAP.

**Defeito identificado e corrigido:** em `weekly_planning_api._planning_slot`, exclusões explícitas e automáticas eram verificadas só depois de `_transformation_candidates`. A receita com leite podia parecer elegível no passo de resgate, pelo que a variante leite sem lactose/arroz era descartada por não melhorar o Plan-Fit nem as preferências; a seguir a receita base era rejeitada pela exclusão. Agora as exclusões são aplicadas à base **antes** da geração de alternativas; após a transformação, todas as exclusões voltam a ser verificadas contra os ingredientes efetivos da variante.

- Código: `2e849759`.
- Teste de regressão: `e878deb5`, com duas pessoas sintéticas, receita de cereais com leite e exclusão explícita desse ingrediente. Exige proposta de transformação válida e seleção da refeição.
- Não altera regras clínicas, dados familiares, configurações de utilizadores, rótulos ou receitas originais. Uma receita continua por confirmar se restarem bloqueios nutricionais, ingredientes sem evidência ou restrições incompatíveis.
- **Verificação pendente:** API CI no SHA final; versão local do catálogo; execução e diagnóstico com as regras e presenças reais do dia 22, que não estão acessíveis a partir do GitHub. Os 11 candidatos da captura não provam, por si sós, que os perfis de leite já estejam no PostgreSQL local. O `deploy.ps1` só aplica `local_db_update` quando a API precisa de atualização/reinício; validar catálogo se a carga local ainda falhar.


## v2.0.96 — catálogo de pães comerciais em revisão (22/11/2026)

Os produtos foram confirmados nas páginas públicas do Auchan e Continente em 22/11/2026 e registados como **candidatos de substituição, não opções clinicamente low FODMAP**:

| Chave estável | Marca / fornecedor | Embalagem | Fonte | Estado |
| --- | --- | ---: | --- | --- |
| `bread-review:auchan-white-400g` | Auchan / Auchan | 400 g | https://www.auchan.pt/pt/alimentacao/mercearia/tostas-e-pao-embalado/pao-embalado/pao-de-forma-auchan-sem-gluten-400g/3509556.html | FODMAP por validar |
| `bread-review:schar-white-sliced-250g` | Schär / Continente | 250 g | https://www.continente.pt/produto/pao-branco-fatiado-sem-gluten-schar-6541632.html | FODMAP por validar |
| `bread-review:auchan-white-300g` | Auchan / Auchan | 300 g | https://www.auchan.pt/pt/alimentacao/mercearia/tostas-e-pao-embalado/pao-embalado/pao-auchan-forma-sem-gluten-300g/3241708.html | FODMAP por validar |

**Implementação:** `development_bread_review_seed.py` cria apenas três `FoodItem` partilhados com fonte comercial, lista publicada de ingredientes, indicação de alergénios/composição a confirmar e estado explícito de revisão em `description`. Não preenche `FoodCompositionSnapshot` com valores supostos, não cria receitas familiares nem altera as originais. A atualização local `local_db_update.apply_catalogue_updates` regista os três candidatos e associa, para cada família existente, quatro `FoodTransformationProfile` no grupo `bread-for-breakfast` (pão para torrada original mais três candidatos); **todos ficam inicialmente com `auto_transform_enabled=False`**. Não altera um perfil ou nome já existente nem volta a aplicar as escolhas padrão nos reinícios. Chaves e UUIDs estáveis impedem duplicação.

A UI pode apresentar os produtos no catálogo de ingredientes com nome, fonte e estado, para substituição **manual e revista**. A substituição automática de pão e as duas trocas simultâneas na mesma receita (leite + pão) continuam pendentes de `#77` e de suporte a múltiplas operações no contrato e na persistência. Não afirmar conclusão dessa parte apenas por existir catálogo. Os testes `test_development_bread_review_seed.py` cobrem idempotência, perfis desativados, nutrição desconhecida e preservação de escolhas. Revalidar CI no último SHA.

Nota: `sem glúten` não equivale a low FODMAP; o produto Auchan 400 g declara fibras vegetais sem origem suficiente na descrição comercial para concluir a adequação clínica. Confirmar sempre rótulo atual, porção, ingredientes e tolerâncias por pessoa. Nunca modificar dados familiares reais em E2E.


### Visibilidade no catálogo de ingredientes

Em `IngredientCatalogue.tsx`, as entradas `source=development-bread-review` apresentam explicitamente **«Candidato comercial · FODMAP por validar · rever ingredientes e porção»** (e tradução EN). Não recebem estado `nutritionReady` nem ficha de composição inventada, e não podem ser aprovadas apenas por serem sem glúten. Ref: commit `c7c8627`. Os links de fornecedor persistem em `FoodItem.source_reference`; o endpoint de ingredientes atual não expõe ainda este campo na UI, pelo que a consulta pública de rótulo permanece na documentação/catálogo até ampliar a API.


## v2.0.97 — rotação dos jantares na geração da próxima semana (22/11/2026)

**Captura reproduzível em termos de sintoma (não base de dados):** proposta para 23–29/11 contém 7 jantares mas apenas 4 pratos distintos na captura: `Frango rápido` 2×, `Salmão no forno com ervinhas da provença` 2×, `Bifanas com natas` 2× e `Escalopes ao vinho Madeira` 1×. Os cartões `Por verificar` / `Proposta` não demonstram aprovação nutricional de cada opção. Este ecrã é o modo `prepare`, que monta `PlanningJourney → WeeklyProposalPreview.generateProposal → weekly_planning_api → shared_weekly_search`. Não corresponde ao mapa `mode=week`, que só gera automaticamente pequeno-almoço.

**Porque acontece:** os candidatos vêm de `getRecommendationBootstrap`, são filtrados por `suitable_meal_types` e limitados a 100 por tipo em `recommendationPlanning.ts`; depois exclusões/Plan-Fit por pessoa podem eliminar mais receitas. `SharedWeeklySearch` usa pesquisa limitada (`max_combinations=256`) se o espaço exceder esse número. A ordenação dava precedência a suporte semanal advisory e/ou pontuação à diversidade, e o número de repetições contava todas as refeições, não especificamente o jantar. A consulta não dá acesso à base PostgreSQL da família: não é correto concluir que todas as receitas existentes eram elegíveis.

**Mudança implementada sem relaxar regras obrigatórias:** o número de jantares que repetem a mesma `candidate_key` passa a ser critério de desempate prioritário **depois de suporte nutricional obrigatório**, antes de suporte advisory e pontuações flexíveis, tanto na busca exaustiva como na limitada. O número total de repetições, variedade por categorias/proteínas e pontuações individuais continuam em vigor. A regra não garante sete jantares diferentes se só existirem menos alternativas elegíveis ou se houver limitações obrigatórias.

**Diagnóstico necessário para verificar dados reais:** definir `NUTRIFLOW_WEEKLY_DEBUG=1` **antes de iniciar a API**; o backend regista `ROTATION dinner-pool` com número de candidatos oferecidos, avaliados e elegíveis em cada dia, e `SEARCH result` com `distinct_dinners` e `repeated_dinners`. Não ativar logs detalhados com informações sensíveis em produção. Verificar os candidatos eliminados (Plan-Fit/ingredients) antes de aumentar indiscriminadamente o limite de 100 ou as operações de substituição.

Código: `shared_weekly_multi_slot_planning.py`, `shared_weekly_search.py`, `weekly_planning_api.py`. Testes `test_shared_weekly_search.py`: rotação de 3 e de 7 jantares elegíveis, respetivamente com pesquisa exaustiva e limitada. Commits `bae41bf`, `dd9f834`, `be8220f`, `632c50b`. CI ainda por confirmar no SHA final.


## v2.0.98 — Windows deploy: Uvicorn saudável sem PID TCP (22/11/2026)

**Regressão observada no Windows do utilizador:** após pull `26e75188..9d044db5`, PostgreSQL e `app.local_db_update` terminam; `StopManaged` termina o PID 60956 da API. O `Launch` inicia Python PID 42828, e `GET /openapi.json` responde com título `NutriFlow AI`, mas `Listener(8000)` devolve zero owners e `VerifiedServiceProcess` retorna `null`, abortando o deploy em `api responded but its listening process is not verified as NutriFlow`.

**Correção:** o `Launch` da API só pode aceitar o **PID que o próprio script acabou de iniciar**, após porta livre confirmada, se o processo Python continuar ativo, executável `.venv/Scripts/python.exe` e argumentos `-m uvicorn app.main:app --host ... --port 8000` forem os mesmos, a API devolver identidade OpenAPI esperada, e não surgir um proprietário TCP contraditório. Marca `trusted_launch` apenas nesse caso. `StateEntry` admite o PID confiável em reinícios posteriores com verificação independente da data de início guardada e da assinatura HTTP; a exceção não se aplica a processos adotados. Teste puro `-VerifyApiCandidateOnly` cobre aceitação sem dono TCP e recusa de PID/executável alheios.

Commit `93e8686`. Commits `34cc830` e `6ea1aab` corrigem a ordem de imports do seed de pão e teste associada à falha Ruff do CI anterior. A compilação e os testes Windows CI ainda têm de passar; não declarar o deploy corrigido no computador até execução local.

**Instrução de atualização:** no terminal Windows, a branch deverá ter as alterações sincronizadas; `git pull --ff-only origin codex/ux-drawer-next-batch-20261119` e `.\\deploy.cmd`; se persistir, recolher `.\\deploy.ps1 -Diagnose` e os últimos registos em `.nutriflow-local\\api.err.log`. Não terminar manualmente processos que não sejam identificados como NutriFlow.


## Lote UX em desenvolvimento — pesquisa de substituições familiares (22/11/2026)

**Defeito identificado na captura de 23–29/11:** os cartões de proposta com variante ou substituição já registada mostravam `Adaptar` / `Por verificar`; pratos sem proposta registada apareciam apenas como `Proposta`. Esta diferença era causada por `WeeklyProposalPreview.tsx` depender da existência de `variant_changes`, `transformation`, `ingredientProposals` ou correspondência em `recipeAdaptations`. **Não existia evidência de que uma proposta sem substituição fosse compatível.** Isto ocultava necessidades de investigação.

**Alterações de UX e fluxo já publicadas:**
- No planeamento semanal, todas as novas propostas de receita sem evidência de adaptação são explicitamente **`Por verificar`**, nunca implicitamente prontas.
- Receitas sem ficha de ingredientes/revisão ou com exclusões sem substituição são assinaladas a **vermelho** como `Investigar ingredientes`. A cor significa trabalho/evidência pendentes, não reprovação clínica inferida.
- Na etapa `Planeamento → Rever refeições`, o componente `AdaptationResearchQueue` deriva uma fila **do catálogo persistido de ingredientes e das exclusões familiares atuais**. Mostra receita, ingrediente e quantidade, estado de proposta, links de pesquisa Monash, Auchan e Continente e um formulário de registo de alternativa.
- `Guardar para revisão` usa o serviço `recipe-adaptations` já existente, com nome concreto e notas/fonte; não marca substituição como `reviewed`, não atribui doses/nutrição fictícias, não cria variante nem altera a refeição/compras. O formulário exige nome e permite documentar URL, dose e dúvidas.
- `Copiar investigação para IA` produz um briefing estruturado com ingredientes pendentes e pedidos explícitos de comprovação por rótulo, porção, fonte e data. **A pesquisa externa por IA ainda não é um serviço automático no backend; o botão copia o pedido para uma IA e há links diretos para pesquisa.** Não confundir isto com pesquisa/validação concluída.
- Variantes de receita existentes continuam listadas como `validar por pessoa e porção`; uma variante `active` não garante elegibilidade na refeição atual.
- Testes Vitest `AdaptationResearchQueue.test.tsx`: exclusões, ausências de alternativas, variantes pré-existentes, links e resumo para IA.

**Próximos passos funcionais ainda necessários**: serviço de pesquisa com fontes autorizadas e revisão humana, fila própria persistida com atribuição/estado de investigação e interface de consentimento, importação de rótulos reais e evidência nutricional/FODMAP por porção, reevaluar regras por cada pessoa, e desenvolver operações múltiplas (Issue #77) de substituição leite + pão na mesma receita. Não relaxar exclusões nem declarar compatibilidade sem verificação. A regeneração da semana nunca deverá adicionar receitas duplicadas ou alterar familiares sem confirmação.

Commits: `3e7105e`, `b4d77f2`, `947f7e0`, `be4f4ac`, `401e36c`, `6ca272c`, `075afcf`, `77ac234`, `8f6cde4`, `ea49123`, `27b968b`. Ainda requer Web CI e UX E2E no último SHA.


## Lote em revisão — diagnóstico completo da seleção e referências FODMAP (22/11/2026)

**Observação do utilizador:** semana 23–29/11 repetia, entre dezenas de receitas, frango rápido, bifanas com natas, escalopes ao vinho Madeira e salmão. A lista de investigação exportada tem dezenas de ocorrências de alho, cebola, leite, iogurte, cogumelos, massas de trigo, muesli, maçã e leguminosas, muitas já com `proposta a rever`.

**Falha confirmada no frontend:** `getRecommendationBootstrap` devolve catálogo ordenado alfabeticamente; `recommendationCandidates` removia silenciosamente tudo após os primeiros 100 candidatos válidos. Assim receitas posteriores não eram sequer avaliadas. Agora, quando ultrapassa 150, são selecionadas 150 posições **distribuídas por todo o catálogo**, deterministicamente; abaixo disso nenhuma receita é eliminada pelo limite. Isso reduz o viés de ordenação, mas não garante elegibilidade nem cobertura exaustiva. Testes para 240 receitas asseguram primeira, média e última e ausência de duplicados.

**Debug por fases:** `WeeklyProposalPreview.generateProposal` em modo opt-in no browser (`localStorage.setItem("nutriflow.weekly.debug", "1")`) regista `bootstrap`, `manuallyRejected`, `wrongMealType`, `wrongSource`, `suitableForBackend`, `forwarded`, `capped` e nomes excluídos pelo teto. Na API, `NUTRIFLOW_WEEKLY_DEBUG=1` e `NUTRIFLOW_WEEKLY_DEBUG_VERBOSE=1` (definidas **antes do arranque do processo Uvicorn**) registam **todos** os candidatos avaliados, `eligible/rejected` e `reasons` de avaliação partilhada e Plan-Fit, resumo por slot e escolha final de jantar. Não é uma autorização para aceitar candidatos que falharam regras. Logs locais podem conter nomes de receitas e regras; não publicar sem rever.

**Referências investigadas:** `docs/nutrition/investigacao-substituicoes-2026-11-22.md` reúne 11 grupos de ingredientes, fontes Monash e exemplos de Auchan/Continente com URLs, ingredientes comerciais publicados quando confirmados e razões de dúvida. `adaptationResearchReferences.ts` expõe essas hipóteses na fila `AdaptationResearchQueue`; escolher apenas **preenche uma proposta**, a guardar manualmente e sem dose automática. Evitar duplicados de mesma alternativa por ingrediente. A investigação por IA com recolha automática de informação externa continua pendente; usar links estáticos e briefing de pesquisa não é ainda um serviço autónomo.

**Diagnóstico local recomendado (terminal e browser):**

```powershell
$env:NUTRIFLOW_WEEKLY_DEBUG = "1"
$env:NUTRIFLOW_WEEKLY_DEBUG_VERBOSE = "1"
.\deploy.cmd -ForceRestart
Get-Content .\.nutriflow-local\api.out.log -Tail 160
```

Antes de gerar nova proposta no browser, abrir DevTools (F12), Console:
```javascript
localStorage.setItem("nutriflow.weekly.debug", "1")
```

Gerar a proposta e guardar os eventos `[NutriFlow WEEKLY]` da consola e `[CANDIDATE-VERBOSE]` / `[ROTATION-VERBOSE]` no log da API. Não apagar o plano atual para diagnosticar: as propostas são read-only até confirmação; o botão pode recalcular apenas os slots por decidir. Repor variáveis/flag em 0 depois.

**Ainda não demonstrado**: número exato de receitas disponíveis por pessoa e os bloqueios concretos da família na base local, se o solver limitado a 256 combinações encontra o melhor plano, nem compatibilidade FODMAP das substituições propostas. Não confundir o estado `proposta a rever` com elegibilidade. Exige revisão de rótulos, dose e regras por participante, e suporte multi-operação pendente na Issue #77.

Commits principais: `9422f7d` (rejeições detalhadas), `1b9fa29` e `1b8400a` (amostragem de catálogo e teste), `a841da0`, `fd2b91c`, `78a8b24` (referências de investigação), `6e5bc00` (documentação nutricional), `0fb4561` (diagnóstico do frontend). CI por validar no SHA final.


## Windows deployment: múltiplos proprietários TCP na porta 5173 (22/11/2026)

O utilizador executou `NUTRIFLOW_WEEKLY_DEBUG=1`, `NUTRIFLOW_WEEKLY_DEBUG_VERBOSE=1`, `deploy.cmd -ForceRestart` na branch do PR #76. Após atualização `d9159326..3946159a`, migrations e catálogo bem-sucedidos, e paragem do frontend gerido PID 89828, `VerifiedServiceProcess` abortou com `Port 5173 has multiple owners; inspect before restarting.` antes de imprimir diagnóstico. Isto ocorreu na verificação do novo listener, não é evidência de falha de Vite nem do planeador.

**Defeito no script:** a comparação de `Listener(5173)` agrupava escutas IPv4 e IPv6 e exigia que todos os seus PIDs fossem idênticos, embora o Vite seja lançado explicitamente em `127.0.0.1` (IPv4). Agora `SelectLoopbackSocketOwner` usa a escuta exclusiva de `127.0.0.1` / `0.0.0.0`, ignorando uma escuta IPv6 não relacionada apenas quando existe exatamente um proprietário IPv4. Se há zero proprietários IPv4, dois proprietários IPv4 diferentes, identidade do processo sem prova ou assinatura Vite inválida, mantém-se a recusa e são exibidos `Show-PortDiagnostics` com os PIDs sem matar processos. A seleção do Node lançado também usa o mesmo critério IPv4, verificando executável Node, script Vite real, data de arranque e assinatura HTTP Vite. CI sintético mantém um caminho próprio para fixture sem endpoint `/@vite/client`. Regressão pura incluída em `-VerifyApiCandidateOnly`.

Commits `0e98765`, `598fc1d`, `df46631`. **Hipótese IPv4/IPv6 ainda não confirmada pelos PIDs do Windows real**, pois o log original não indicou os seus endereços. Esperar CI e repetir `.\\deploy.ps1 -Diagnose` após `git pull --ff-only origin codex/ux-drawer-next-batch-20261119`. Se houver proprietários IPv4 distintos, não os terminar automaticamente; pedir diagnóstico para identificar cada processo.
