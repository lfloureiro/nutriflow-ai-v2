# Lote visual — viewport das cinco referências aprovadas (21/11/2026)

## Fonte de verdade
- Semana: desenho aprovado v2.0.86; preservar a composição e os dados reais.
- Outras rotas: `docs/ux/references/manifest.json`, cinco alvos aprovados a **1672 × 941 px**: `inicio.png`, `receitas.png`, `familia.png`, `compras.png` e `despensa.png`.
- Os PNG binários ainda **não constam da árvore Git**. O manifesto e os hashes estão presentes; as cópias originais existem na Biblioteca do projeto. Não substituir por imagens genéricas, nem declarar paridade pixel a pixel.

## Implementado neste lote
- `apps/web/e2e/approved-reference-viewport.spec.ts`: novo teste Chromium, com família sintética de quatro membros, em **dark e light**, para os cinco destinos reais, sempre a 1672 × 941 CSS px.
- Guarda dez capturas `reference-<ecrã>-<tema>-1672x941.png` para a comparação manual/automática futura com os PNG exatos.
- Impõe o shell lateral comum (largura 310–321 px), a ausência de overflow horizontal, o ajuste dos blocos principais do Início dentro do viewport e a conservação dos quatro membros com scroll interno na área própria.
- `.github/workflows/ux-e2e.yml`: recolhe os novos PNG sintéticos no artefacto `screen-visual-<SHA>`, mesmo quando o teste falhar.
- Não altera API, PostgreSQL, dados reais, receitas ou a Semana. PR #76 permanece draft.

## Próxima verificação obrigatória
1. Confirmar Web CI, API CI e UX E2E no mesmo SHA deste lote. O commit do teste não equivale a execução bem-sucedida.
2. Inspecionar as dez capturas E2E contra os PNG originais do manifesto. Sem esses binários disponíveis no runner, não calcular falsos pixel-diffs.
3. Continuar a correção de proporções reais, nomeadamente Início a 100% de zoom, Receita/Família com dados preenchidos, Compras e Despensa com listas de dimensão real.
4. Apenas considerar o ecrã visualmente aceite após comparação com a referência, sem perder as interações, drawers, dados nutricionais ou os estados vazios legítimos.
