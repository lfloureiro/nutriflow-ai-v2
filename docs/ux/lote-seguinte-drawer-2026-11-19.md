# Lote seguinte — drawer, contexto e restrições individuais (19 novembro 2026)

**Base:** main em `d922eecd32f1848a5c2345367fe910ca720c7c92` (PR #75).  
**Fonte visual prioritária:** `Casa_a_Mesa_Prototipo.html` enviado nesta conversa, versão com tema escuro carvão/âmbar e drawers de 620/780 px. O ficheiro enviado não se encontra automaticamente no checkout do repositório. Comparar sempre visualmente com essa referência, não com o ZIP v3 anterior.  
**Fonte funcional prioritária:** `docs/handoff-2026-11-19.md` e `docs/ux/aceitar-trocas-e-refeicao.md`.  
**Estado:** apenas o primeiro componente base deste lote começou nesta branch; não declarar UX-007/008/024/027 concluídos.

## Checklist de 12 tarefas — pela ordem de dependências

- [x] **01 — Componente base de drawer acessível.** Criar um painel reutilizável responsivo, sem regras clínicas ou dados embutidos, com foco inicial e restaurado, Escape, bloqueio de scroll, aria-modal, título acessível, adaptação a mobile e movimento reduzido. **Estado:** código adicionado; testes ainda pendentes.
- [ ] **02 — Testar o drawer isoladamente.** Cobrir foco inicial/retorno, Tab/Shift+Tab, Escape, fundo inacessível, mobile, 200% zoom, temas e múltiplos ciclos abrir/fechar.
- [ ] **03 — Converter detalhe da refeição em contexto lateral.** Na semana, manter visível o mapa ao abrir uma refeição; preservar a célula/dia/modo e não duplicar edição nem motores nutricionais.
- [ ] **04 — Guardas e recuperação de contexto.** Fechar drawer, navegar e voltar apenas após resolver alterações por guardar; URL e browser back/forward recuperam refeição/aba; erro e reload não perdem rascunho guardado.
- [ ] **05 — Migrar o fluxo de adaptação corrigido para o drawer.** Aceitar proposta diretamente → rever receita preenchida (edição opcional) → confirmar no plano; conservar rascunhos, herança de unidade/quantidade/rendimento ausente e a identidade de ingredientes declarados.
- [ ] **06 — Detalhe por pessoa sem aprovação implícita.** Mostrar presença, dose, regra e fonte; separar adequação nutricional, preferência/estrelas e estado desconhecido; evitar criar score sem evidência.
- [ ] **07 — Uniformizar formulários secundários.** Aplicar os mesmos padrões a receita, ingrediente e pessoa, sem tornar rendimento, preparação ou valores de energia obrigatórios.
- [ ] **08 — Rever ações e layout nos quatro tamanhos.** 1440, 1024, 768 e 390 px, claro/escuro; sem overflow, regressos coerentes ou cortes nas ações.
- [ ] **09 — Completar painel de restrições individuais.** Alergias, intolerâncias, exclusões, preferências, tolerâncias, validade, fonte e incerteza, sem inferir protocolo FODMAP a partir de diagnóstico.
- [ ] **10 — Integrar plano profissional e autoridade.** Mostrar origem/versão/validade de regras, separar importação revista de ativação e impedir que informação desconhecida seja contada como segura.
- [ ] **11 — Presenças reutilizáveis e contextos individuais.** Padrões por dia/slot, ausente versus por confirmar, exceções e visitantes; alterar participantes revalida elegibilidade sem sobrescrever escolhas fixadas.
- [ ] **12 — Regressão integrada e handoff.** API/PostgreSQL reais em DB sintética isolada, teste de gravação/reload e compras, testes web/API, migrations se aplicável, evidências e cross-check visual; não tocar na família principal.

## Invariantes de implementação

1. `source=family_adaptation` / `confirmation_mode=recipe_edit` não validam nutrição clínica. Restrições obrigatórias conhecidas continuam bloqueantes.
2. Receitas originais, snapshots históricos e outras refeições não são alterados por uma adaptação selecionada.
3. Dados não disponíveis continuam desconhecidos; não converter embalagens sem evidência.
4. Não usar números ilustrativos, entrevistas simuladas ou métricas sintéticas como métricas reais de ML.
5. Não incluir `.env`, backups, IDs familiares, fotografias privadas ou capturas de ecrã reais no Git.
6. Não fazer merge em main sem validação local e CI no SHA exato e autorização na sessão correspondente.

## Próxima frente académica (após estabilização UX)

UX-021/049 (importação NLP com revisão) → UX-051 (eventos/dataset temporal) → UX-052 (recomendador treinado com baseline e teste retido) → UX-022/053 (corpus anotado e embeddings) → UX-054/055 (explicações, proveniência e operação). Separar treino sintético do resultado real e documentar cobertura/limitações.

## Evidência desta abertura

A branch foi criada a partir de main; apenas os ficheiros indicados no commit da branch foram modificados. Nesta sessão, o checkout local do repositório, a DB local e o preview local do utilizador **não estão acessíveis**. Não reportar testes npm/pytest, E2E ou CI como realizados até serem executados e observados.
