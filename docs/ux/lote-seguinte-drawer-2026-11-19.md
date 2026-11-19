# Lote seguinte — drawer, contexto e restrições individuais (19 novembro 2026)

**Base:** main em `d922eecd32f1848a5c2345367fe910ca720c7c92` (PR #75).  
**Fonte visual prioritária:** `Casa_a_Mesa_Prototipo.html` enviado nesta conversa, versão com tema escuro carvão/âmbar e drawers de 620/780 px. O ficheiro enviado não se encontra automaticamente no checkout do repositório. Comparar sempre visualmente com essa referência, não com o ZIP v3 anterior.  
**Fonte funcional prioritária:** `docs/handoff-2026-11-19.md` e `docs/ux/aceitar-trocas-e-refeicao.md`.  
**Estado:** apenas o primeiro componente base deste lote começou nesta branch; não declarar UX-007/008/024/027 concluídos.

## Checklist de 12 tarefas — pela ordem de dependências

- [x] **01 — Componente base de drawer acessível.** Criar um painel reutilizável responsivo, sem regras clínicas ou dados embutidos, com foco inicial e restaurado, Escape, bloqueio de scroll, aria-modal, título acessível, adaptação a mobile e movimento reduzido. **Estado:** código adicionado; testes ainda pendentes.
- [ ] **02 — Testar o drawer isoladamente.** Cobrir foco inicial/retorno, Tab/Shift+Tab, Escape, fundo inacessível, mobile, 200% zoom, temas e múltiplos ciclos abrir/fechar. **Parcial validado no E2E:** foco inicial/retorno, Tab/Shift+Tab, Escape, `inert`, mobile, 2 temas, fecho/reabertura após history/reload. Falta zoom 200% real e auditoria completa de acessibilidade.
- [x] **03 — Converter detalhe da refeição em contexto lateral.** Na semana, manter visível o mapa ao abrir uma refeição; preservar a célula/dia/modo e não duplicar edição nem motores nutricionais. **Implementação ligada, regressão visual e E2E pendentes:** editor manual e detalhe de avaliação/adaptação semanal utilizam o drawer; transição detalhe → editor evita dois diálogos em simultâneo.
- [ ] **04 — Guardas e recuperação de contexto.** Fechar drawer, navegar e voltar apenas após resolver alterações por guardar; URL e browser back/forward recuperam refeição/aba; erro e reload não perdem rascunho guardado. **Parcial:** URL com `date`, `mode=week` e `meal=...` adicionada para os quatro tempos, seleção/fecho sincronizados e testes unitários do parser. Navegação browser/rascunhos ainda aguardam E2E.
- [ ] **05 — Migrar o fluxo de adaptação corrigido para o drawer.** Aceitar proposta diretamente → rever receita preenchida (edição opcional) → confirmar no plano; conservar rascunhos, herança de unidade/quantidade/rendimento ausente e a identidade de ingredientes declarados. **Parcial validado em API E2E:** receita editada com ingrediente conhecido ou declaração textual preserva quantidade, unidade e valores ausentes; só altera plano/compras após confirmação. Faltam teste completo dos botões no navegador e rascunhos.
- [ ] **06 — Detalhe por pessoa sem aprovação implícita.** Mostrar presença, dose, regra e fonte; separar adequação nutricional, preferência/estrelas e estado desconhecido; evitar criar score sem evidência. **Parcial:** regras e fontes por pessoa, estado desconhecido explícito, porções registadas ou propostas com quantidade/unidade originais; propostas distinguem pessoas consideradas de presenças confirmadas. Faltam distinção completa entre preferências/estrelas e cobertura do E2E de todas as fontes.
- [ ] **07 — Uniformizar formulários secundários.** Aplicar os mesmos padrões a receita, ingrediente e pessoa, sem tornar rendimento, preparação ou valores de energia obrigatórios. **Implementação alargada, E2E pendente:** condições de saúde, perfil, criação de pessoa, receita e ingrediente usam proteção de rascunho; receitas/ingredientes partilham padrões de superfícies e espaçamento. Falta revisão visual nos quatro tamanhos.
- [ ] **08 — Rever ações e layout nos quatro tamanhos.** 1440, 1024, 768 e 390 px, claro/escuro; sem overflow, regressos coerentes ou cortes nas ações. **Parcial validado no E2E:** plano semanal + drawer em todas as oito combinações sem overflow horizontal. Restam formulários e ações de outros ecrãs, verificação visual humana e zoom.
- [ ] **09 — Completar painel de restrições individuais.** Alergias, intolerâncias, exclusões, preferências, tolerâncias, validade, fonte e incerteza, sem inferir protocolo FODMAP a partir de diagnóstico.
- [ ] **10 — Integrar plano profissional e autoridade.** Mostrar origem/versão/validade de regras, separar importação revista de ativação e impedir que informação desconhecida seja contada como segura.
- [ ] **11 — Presenças reutilizáveis e contextos individuais.** Padrões por dia/slot, ausente versus por confirmar, exceções e visitantes; alterar participantes revalida elegibilidade sem sobrescrever escolhas fixadas.
- [ ] **12 — Regressão integrada e handoff.** API/PostgreSQL reais em DB sintética isolada, teste de gravação/reload e compras, testes web/API, migrations se aplicável, evidências e cross-check visual; não tocar na família principal. **Parcial:** testes reais com PostgreSQL temporário cobrem plano, drawer, ingrediente, concorrência, confirmação de adaptações e refresh das compras; restam percursos UI de adaptação/compras e cross-check visual completo.

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

## Incremento de código iniciado nesta branch

- `apps/web/src/ui/ContextDrawer.tsx` e `.css`: drawer por portal, tokens dos dois temas, foco inicial/retorno, Tab/Shift+Tab, Escape, `inert` do conteúdo principal, scroll bloqueado, mobile e movimento reduzido.
- `apps/web/src/FamilyMeals.tsx`: o editor manual de uma refeição abre nesse drawer sem substituir a semana ou o dia. A chamada de fecho usa `useUnsavedChanges.confirmDiscard()` já existente. Gravação/remoção continuam nos mesmos endpoints e sem alteração de contratos.
- Verificação nesta sessão: presença dos ficheiros e dos pontos de integração na branch; **não equivale a compilação TypeScript, Vitest ou E2E**. Abrir/fechar, rascunhos, edição manual, alterações de tema e responsive continuam por testar no ambiente de execução antes de PR/merge.
- A referência visual enviada nesta conversa não deve ser substituída pela cópia anterior do ZIP. Nenhum dado da família real foi consultado ou alterado nesta branch.

## Continuação do incremento

- `apps/web/src/WeeklyProposalPreview.tsx`: detalhe da refeição guardada, proposta, avaliação por pessoa e componente existente `SelectedMealOptions` aparecem no drawer responsivo, sem alterar os serviços de adaptação, compras ou planeamento. Removido o scroll automático para o detalhe inline.
- O fecho do detalhe passa por `requestNavigation()`, respeitando bloqueios existentes de alterações não guardadas; abrir o editor fecha o drawer de detalhe para não acumular dois diálogos.
- PR de CI criado em modo **draft**: https://github.com/lfloureiro/nutriflow-ai-v2/pull/76. Não integrar sem gates verdes no último SHA e validação E2E isolada.
- Resultado anterior de CI web no SHA `86356b2731dce8ea5700fb214c8e3ac7bc909217`: success; **não valida os commits posteriores de integração semanal**.

## Próximo incremento — endereço direto por refeição (19 novembro 2026)

- A URL do plano semanal aceita `#/meals?date=AAAA-MM-DD&meal=dinner&mode=week` para restaurar o drawer. Valores inválidos de `meal` são ignorados e o estado só é interpretado na vista semanal, com data válida.
- Selecionar/fechar detalhe sincroniza o URL via navegação da aplicação; o fecho e a troca de contexto respeitam `requestNavigation()` e os bloqueios existentes.
- O parser recebeu testes de roundtrip e de parâmetros indevidos. **Ainda falta executar E2E real em navegador**, sobretudo back/forward e regresso a alterações não guardadas. Não classificar a tarefa 04 como concluída.
- O utilizador confirmou visualmente o drawer anterior em desktop e referiu bom comportamento em mobile. Isso não substitui testes de teclado nem regressão automatizada.

## Incremento — regras por participante e proveniência (19 novembro 2026)

- `SelectedMealOptions` passou a expor uma secção expansível de restrições individuais, **apenas após resposta da API de restrições**. Filtra pessoa, data e tempo de refeição; preserva tipo/descrição da fonte, avisos e estado sem regras devolvidas, sem chamar seguro ou adequado a nenhum destes estados.
- A apresentação é compacta no drawer para desktop e mobile e usa os tokens claro/escuro existentes; não muda o motor, os contratos de dados, nem faz qualquer gravação na base.
- `SelectedMealOptions.test.ts` acrescenta casos de participantes presentes/ausentes, dias distintos, horários distintos, avisos e ausência de regras. A CI web foi acionada para o último SHA e precisa de passar antes de pedir teste manual.
- **Pendentes:** avaliação end-to-end com API real numa DB sintética, visita a 1440/1024/768/390, confirmação de contraste/teclado e comparação com o HTML aprovado. Não houve acesso à família do utilizador.

## Incremento — proteção de alterações em saúde individual (19 novembro 2026)

- `PersonHealthConditions`: formulário distingue abertura sem modificações de alterações reais. Ao navegar, fechar/recarregar a página, trocar de condição ou cancelar, um rascunho modificado pede confirmação de descarte. Guardar mantém os contratos API atuais e preserva revisões anteriores.
- `dietary-review.css`: campos e ações mais compactos no formulário secundário e disposição de uma coluna em mobile, preservando tokens dos temas aprovados e foco existente.
- Testes `PersonHealthConditions.test.ts`: verificação de formulário intacto, fonte/datas/notas alteradas e reposição do valor original.
- **Sem alteração do esquema de dados, sem dados clínicos inventados e sem leitura/escrita na família real.** Testes unitários são insuficientes para declarar a proteção completa sem E2E de navegação por separadores e refresh, ainda pendente.

## Incremento — evitar perda de alterações entre separadores (19 novembro 2026)

- `PersonOverview` consulta os bloqueios de edição antes de mudar de secção local. Corrige o caso em que a pessoa estava a editar uma condição de saúde e passava para Nutrição/Perfil sem confirmação, porque essa navegação não usava URL.
- `PersonProfileEditor` passa a usar `useUnsavedChanges`: aviso por conteúdo realmente modificado, confirmação ao cancelar, navegação bloqueável e `markSaved` após resposta positiva da API.
- `PersonSetupForm` passa a proteger rascunhos, inclusive campos energéticos opcionais e opções de fornecedores; a criação continua a pedir apenas os dados obrigatórios já existentes. O botão «Fechar» no ecrã Pessoas também consulta os bloqueios.
- A proteção é apenas frontend. Ainda é necessário validar o percurso em navegador, inclusive confirmar uma única vez, cancelar e voltar, e regressão entre pessoas. A base real não foi alterada.

## Incremento — editor de ingredientes e apresentação de receitas (19 novembro 2026)

- O editor de ingredientes passa a proteger rascunhos em caso de saída para outro ecrã, botão de voltar, reload e tentativa de ativar/desativar um ingrediente. Só marca a edição como guardada após confirmação positiva da API.
- A composição nutricional do ingrediente continua **opcional** quando não há evidência. A função `buildIngredientComposition` mantém `null` sem nutrientes (coberta por teste unitário já existente); não se inventa energia, quantidade ou tolerância.
- O editor de receitas já tinha proteção por `useUnsavedChanges`; não se alterou a validação existente de rendimento, porções, preparação e ingredientes.
- `ux-workflow.css` uniformiza cartões, títulos, margens e campos destes dois formulários, incluindo mobile e os tokens claro/escuro; sem mudar contratos de dados.
- **Ainda pendente:** testar no navegador o descarte/guarda de ingredientes, edição de receitas longas, zoom 200%, acessibilidade de teclado e E2E API/PostgreSQL com base sintética. Não considerar a tarefa 07 encerrada sem evidência.


## Política de versões NutriFlow AI (19 novembro 2026)

Por decisão do utilizador, a aplicação apresenta sempre uma versão `X.Y.Z` junto à marca NutriFlow AI / Casa à Mesa. Primeira versão explicitamente identificada nesta política: **2.0.1**; o valor exposto pelo frontend vem exclusivamente de `apps/web/package.json`, não de uma string duplicada na interface. A versão do serviço API é independente.

- **X — major:** alteração estrutural, incompatibilidade ou mudança substantiva de produto. Pedir ao utilizador teste manual antes de promover a release.
- **Y — minor:** marco funcional consolidado pronto para validação do utilizador. Pedir teste manual apenas quando passar de um Y para o seguinte.
- **Z — patch/incremental:** commits de trabalho diário, correções encontradas nos bugs do utilizador, ajustes UX, regressão e incrementos ainda dentro do Y atual. **Não interromper o utilizador para testes em cada Z**; validar automaticamente cada SHA no CI. Agrupar resultados até ao próximo Y ou X.

Esta é uma política de **cadência de testes**, não dispensa testes de segurança nem permite publicar código com CI vermelho. Se houver um bloqueio grave de dados ou risco de perda irreversível, parar a publicação e reportar o bloqueio; não exigir testes funcionais do utilizador como substituto de testes automatizados.

Ao avançar para um novo Z, atualizar `apps/web/package.json` e o registo de mudanças; o badge atualiza automaticamente. Fazer merge ou publicar releases apenas mediante autorização, manter `main` intacta enquanto PR #76 estiver em rascunho. Manter a automação de estado focada na prontidão do próximo **Y/X**, evitando notificações por patches normais.

## Patch 2.0.2 — regressão de drawer e layouts (19 novembro 2026)

- CI observado no commit `a26b2969ab275bd3770acd2b84d3b5779b2dc604`: **UX E2E sucesso, 6/6 testes Chromium**, run `44539565448`. Testes existentes de dados isolados permanecem; acrescidos foco/Tab/Shift+Tab/Escape/retorno e 1440/1024/768/390 px × claro/escuro com preferência realmente persistida, movimento reduzido e assertivas de overflow. A suite usa PostgreSQL 18 temporário de GitHub Actions; a base local do utilizador não é acedida.
- Web CI e API CI deste incremento são independentes da suite de navegador; confirmar também no SHA final após documentação/versionamento, sem usar o sucesso anterior como prova do último SHA.
- Um primeiro teste de responsividade falhou por alterar a preferência de tema **após** a inicialização e medir o drawer ainda animado; corrigiu-se com storage e reload/reduced motion. Não houve correção de produto inferida a partir dessa falha de teste.
- O código passa a apresentar **v2.0.2**, patch Z: sem pedir nova ronda manual, conforme a política de cadência X.Y.Z. Pendem zoom real, revisão de outros ecrãs, percurso integral de adaptações e sincronização de compras na mesma base sintética. Não marcar tarefas 02/08/12 como 100% concluídas.

## Patch 2.0.3 — pessoas consideradas, porções e proveniência (19 novembro 2026)

- `SelectedMealOptions`: numa proposta ainda não confirmada, a interface diz **«Pessoas consideradas nesta proposta»**, não afirma presença confirmada. Numa refeição guardada identifica **«Participantes no plano»**.
- Secção de restrições por pessoa mostra a dose apenas quando a API forneceu quantidade e unidade para essa pessoa, distinguindo **porção registada** (refeição guardada) de **porção proposta** (recomendação). Sem quantidade conhecida mostra **«Porção não registada»**. Não converte `emb`, não atribui energia e não altera o estado clínico.
- `SelectedMealOptions.test.ts` cobre unidades `emb` e `serving` preservadas e informação ausente. O E2E do drawer passa a verificar a porção guardada de uma pessoa fictícia e que a ausência de regras devolvidas continua explicitamente não-validação.
- Mantém-se a cadência X.Y.Z: correções nesta série 2.0.Z sem solicitar teste manual. Falta CI verde no SHA exato após este documento, regressão completa do motor de adaptações e cenário de vários participantes com alterações de presenças.

## Patch 2.0.4 — corrigir concorrência na atualização nutricional diária (19 novembro 2026)

- A regressão sintética anterior, embora verde, revelou nos logs PostgreSQL violações da constraint `uq_daily_nutrition_states_person_date_version` quando duas chamadas API recalculavam o mesmo estado diário em simultâneo. Um sucesso do frontend **não** significa ausência de erros de concorrência no backend.
- `apps/api/app/services/daily_nutrition_state.py`: bloqueio transacional `SELECT person.id FOR UPDATE` antes de consultar/inserir o estado único, serializando o recálculo por pessoa até commit/rollback. Não modifica schema, cálculo, componentes nem os dados reais da família. Os acessos paralelos seguintes leem o estado já criado no isolamento READ COMMITTED do PostgreSQL.
- `apps/web/e2e/ux-regression.spec.ts`: novo cenário dispara 10 pedidos paralelos para o endpoint planning-bootstrap `ensure_state=true` da mesma pessoa fictícia. Exige 10 respostas HTTP 200 e o mesmo identificador de estado em todas.
- **Evidência:** commit `f22103d8e3d919e1ab6577a31e225fb5e9cb02fd`, workflow UX E2E run `44542190661`, **7/7 testes Chromium passaram**, e o log PostgreSQL da execução não contém a violação de unicidade anteriormente observada. A suite de CI usa PostgreSQL descartável; não tocar na base da família.
- Versão atual **2.0.4** (incremento Z). Próximas frentes: completar aceitação/revisão/confirmar adaptação, compras, contextos individuais e avaliação da autoridade profissional. Sem pedido de teste manual até à próxima X/Y pronta.

## Patch 2.0.5 — confirmar adaptações e atualizar compras (19 novembro 2026)

- A API real e o PostgreSQL sintético em GitHub Actions passaram **9/9 testes E2E**, commit `8cafb2235b03a7753e003988a1505ab6c1359746`, run `44546088492`. Web CI e API CI desse commit também tiveram sucesso.
- Testes novos cobrem criar `recipe_edit` a partir de receita familiar, manter porções, unidades e rendimento herdados, aplicar a variante **apenas à refeição escolhida**, atualizar compras após confirmação e manter a receita original intacta.
- Outra via agora coberta: substituição aceite por descrição, sem associação inicial ao catálogo, cria ingrediente declarado pela família, não atribui energia/nutrientes sem evidência e só aparece nas compras após confirmação.
- Corrigido `apps/api/app/services/recipe_edit.py` para preservar `preparation=None` quando a fonte não tinha preparação e a edição não acrescentou informação. Teste integrado verifica o valor realmente devolvido pela API.
- Acrescentado um décimo cenário de regressão: duas refeições partilham a receita base; uma adapta-se, a outra mantém-se intacta; compras refletem ambos os ingredientes e, ao cancelar apenas a refeição adaptada, removem a necessidade exclusiva dessa adaptação. **Este cenário passou na regressão E2E (run 44547405963).**
- Versão visível: **v2.0.5**. Alteração Z: não pedir teste manual; aguardar avaliação da próxima X/Y. Não declarar concluído o fluxo completo UI sem cobertura de clique em cada etapa.

## Fecho do patch 2.0.5 — evidência funcional (19 novembro 2026)

- SHA de código `dbf7fa33dc55f29eb730279875ee38650355d0e7`: Web CI **success**, API CI **success**, UX E2E PostgreSQL isolado **success**, run `44547405963`, **11/11 testes**.
- Teste 10 confirmou que editar uma refeição entre duas que partilham a receita original não altera a segunda; compras incluem simultaneamente ingredientes originais e adaptados; cancelar a refeição adaptada retira só a sua necessidade da lista.
- Teste 11 executou **os botões da UI**: Preparar as trocas → Rever receita → Usar adaptação guardada → Seguir para confirmação final → Confirmar esta refeição no plano, validando que o aviso **«Escolha da família · não é validação nutricional»** é mostrado antes de guardar e o plano só muda na confirmação.
- `MealAdaptationFlow` deixou de fabricar `eligible=true` para `confirmation_mode=recipe_edit`. A decisão da família não certifica nutrição/segurança clínica; permanece a validação de restrições obrigatórias na gravação pela API.
- Não interpretar os 11/11 como cobertura total: rascunhos incompletos, revisão profissional, presenças excepcionais, aquisições reais e acessibilidade zoom 200% ainda requerem trabalhos específicos.
- O último commit após documentação deverá voltar a passar os três gates. O número visível mantém-se **v2.0.5**, sem solicitar teste manual ao utilizador.
