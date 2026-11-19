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
