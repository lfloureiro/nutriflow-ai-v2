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
