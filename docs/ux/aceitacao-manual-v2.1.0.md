# NutriFlow AI v2.1.0 — plano de aceitação manual

**Estado:** PREPARADO / NÃO LIBERTADO PARA TESTES. Esta checklist serve para a próxima versão minor, não para cada patch 2.0.Z.
**Branch de preparação:** `codex/ux-drawer-next-batch-20261119` / PR #76.
**Ambiente:** ambiente local isolado, backup comprovado, jamais dados familiares reais nos testes automatizados. Registar versão X.Y.Z e commit SHA antes de iniciar.
**Pré-condições de convite:** Web CI, API CI e UX E2E verdes **no mesmo SHA final**, revisão de acessibilidade/zoom e bugs bloqueantes fechados. Uma versão só fica PRONTA PARA TESTE após declaração explícita no handoff.

## Como registar um resultado
Marcar cada cenário como **PASSOU / FALHOU / BLOQUEADO / NÃO TESTADO**, com largura do ecrã, tema, passo em que falhou, comportamento esperado/observado e captura **privada** quando útil. Não fazer upload de capturas, nomes, condições de saúde ou dados familiares para o GitHub.

## A. Entrada, navegação e aspetos visuais
- [ ] A01 — Abrir Home, Semana, Pessoas, Receitas, Ingredientes, Despensa e Compras; nenhuma vista em branco nem erro visível.
- [ ] A02 — Alternar claro/escuro em cada zona; persistência após reload. Escuro carvão/âmbar, sem elementos verdes estranhos.
- [ ] A03 — Desktop 1440 px, 1024 px; tablet 768 px; mobile 390 px: sem scroll horizontal, botões cortados ou sobreposição.
- [ ] A04 — Zoom do browser a 200% e apenas teclado: foco visível, ordem coerente, Escape fecha drawer e devolve foco; sem fuga para fundo.
- [ ] A05 — Endereço direto da Semana por data e refeição; browser back/forward e reload preservam contexto válido.
- [ ] A06 — Versão X.Y.Z visível perto da marca, consistente em todos os ecrãs.

## B. Família, perfis, saúde e preferências
- [ ] B01 — Criar pessoa sem calorias/energia opcionais; reabrir e editar, sem perder campos.
- [ ] B02 — Adicionar condição/restrição com origem, validade e notas; rever a informação e distingui-la de uma regra clinicamente validada.
- [ ] B03 — Editar condição ou perfil, tentar trocar de separador/fechar; cancelar o aviso mantém o rascunho e confirmar descarte abandona-o.
- [ ] B04 — Ver preferências, ingredientes excluídos e estado desconhecido; não confundir ausência de informação com segurança/FODMAP validado.
- [ ] B05 — Plano profissional: confirmar fonte, data, estado ativo/revisto e regras avaliáveis versus orientações não avaliadas. Nunca tratar orientação incompleta como validação.

## C. Receitas, ingredientes e adaptações
- [ ] C01 — Criar receita com ingredientes e porções; não exigir preparação, rendimento ou nutrientes ausentes na fonte.
- [ ] C02 — Criar ingrediente sem composição nutricional; guardar e recarregar continua desconhecido.
- [ ] C03 — Abrir refeição na Semana: drawer mantém grelha visível; informação por pessoa, porções e fontes acessíveis.
- [ ] C04 — Escolher proposta de substituição, aceitar e rever receita preenchida, alterar opcionalmente e confirmar apenas a refeição selecionada.
- [ ] C05 — Antes de confirmação, nem receita original, nem outras refeições, nem compras são alteradas.
- [ ] C06 — Substituição por ingrediente conhecido preserva identidade; descrição livre não recebe energia, nutrientes ou certificação clínica inventados.
- [ ] C07 — Guardar adaptação incompleta, fechar, recarregar e retomar; continua por confirmar e compras não mudam.
- [ ] C08 — Alterar receita de origem de um rascunho; o aviso de revisão da base aparece, sem aplicação automática.
- [ ] C09 — Ao confirmar adaptação, a indicação «Escolha da família · não é validação nutricional» é visível.

## D. Agenda, presença e convidados
- [ ] D01 — Planear semana com pequeno-almoço, almoço, lanche e jantar; distinguir célula proposta, guardada e por preencher.
- [ ] D02 — Criar refeição: Presente/Ausente/Por confirmar; bloqueio da gravação enquanto houver decisões pendentes.
- [ ] D03 — Reutilizar presenças de refeição anterior: não copia quantidades nem altera a refeição origem.
- [ ] D04 — Guardar decisões de presença por semana, recarregar e regressar; distinguir claramente «por confirmar» de «ausente».
- [ ] D05 — Adicionar 2 convidados sem perfil num jantar: visualizar aviso somente nesse jantar; as doses, nutrição e compras não aumentam automaticamente.
- [ ] D06 — Alterar/limpar convidados e recarregar; verificar persistência e ausência de alterações implícitas a participantes já guardados.
- [ ] D07 — Alterar pessoas de uma refeição com restrições conhecidas: pedir revalidação e bloquear incompatibilidades, sem sobrescrever escolha previamente fixada.

## E. Nutrição, despensa e compras
- [ ] E01 — Comparar composição nutricional da refeição com plano profissional ativo quando há dados; sinalizar falta de cobertura quando não há.
- [ ] E02 — Avaliação/estrelas e gosto pessoal não substituem elegibilidade nutricional nem regra obrigatória.
- [ ] E03 — Aplicar semana ou adaptação confirmada: lista de compras reflete ingredientes efetivos e stock utilizável.
- [ ] E04 — Assinalar comprado não equivale a recebido; receção parcial regista quantidade real e lote/validade, sem duplicar por retry.
- [ ] E05 — Retirar refeição adaptada: compras deixam de incluir somente a necessidade dessa refeição, sem apagar a original/outras.
- [ ] E06 — Voltar à aplicação após reload: plano, adaptações confirmadas, despensa e compras conservam os estados.

## F. Idiomas, estabilidade e proteção de dados
- [ ] F01 — Português e inglês: títulos, labels, botões, avisos e mensagens úteis sem strings em bruto.
- [ ] F02 — Testar navegação, drawer e formulários em mobile com teclado virtual, botões operáveis e sem conteúdo oculto.
- [ ] F03 — Simular erro de ligação em alteração ainda não confirmada; não indicar sucesso nem apagar rascunho.
- [ ] F04 — Teste de duas sessões: mudança concorrente causa aviso/reload em vez de sobrescrever silenciosamente.
- [ ] F05 — Confirmar que qualquer base de dados de teste contém apenas registos fictícios e que não houve exposição de dados pessoais.

## Decisão final
- [ ] CI Web/API/UX E2E verde no SHA do candidato a v2.1.0.
- [ ] Sem falhas bloqueantes de integridade, privacidade ou restrições obrigatórias.
- [ ] Evidência visual de 1440/1024/768/390, ambos os temas e zoom 200%.
- [ ] Cada falha documentada, corrigida em patch e retestada.
- [ ] Aprovação explícita para promoção/merge; PR #76 permanece draft até essa decisão.

**Relatório de bug:** `Versão / SHA | cenário | ecrã e tema | passos | esperado | observado | severidade | evidência privada`.
