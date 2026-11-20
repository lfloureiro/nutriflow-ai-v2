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
- [ ] **11 — Presenças reutilizáveis e contextos individuais.** Padrões por dia/slot, ausente versus por confirmar, exceções e visitantes; alterar participantes revalida elegibilidade sem sobrescrever escolhas fixadas. **Parcial:** ao criar refeição, é possível copiar explicitamente apenas os participantes de outra refeição anterior do mesmo slot e mesma semana, sem copiar/alterar quantidades, unidades ou refeições já guardadas. Faltam padrões persistentes por dia/slot, por confirmar, visitantes e revalidação E2E de exceções.
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

## Patch 2.0.6 — continuidade de rascunhos incompletos (19 novembro 2026)

- Adicionada regressão sobre API/PostgreSQL **isolados** para guardar um rascunho com alternativa, quantidade, rendimento e porção em falta; recuperar por receita após nova leitura, atualizar com `expected_version` e rejeitar atualização obsoleta com HTTP 409.
- A asserção verifica que guardar, retomar ou atualizar o rascunho **não** muda `recipe_id` da refeição nem os requisitos da lista de compras. Rascunho não equivale a refeição confirmada.
- Acrescentado E2E **pelos botões do drawer**: escolher ingrediente manualmente, deixar quantidade explicitamente em branco, guardar para continuar depois, recarregar, abrir as trocas e retomar rascunho; verificar que mantém os dados incompletos e não aplica a refeição.
- Versão do frontend passa a **v2.0.6**; é patch Z e não requer validação manual. **Só declarar sucesso após CI Web, API e UX E2E no SHA final**; caso haja falha, usar logs do job e corrigir, sem tocar nos dados reais.
- Ainda pendem revisão com várias pessoas/presenças, rascunho após alteração da receita base, comparação com orientações profissionais e zoom 200%.

## Patch 2.0.7 — sinalizar rascunho após revisão da receita original (19 novembro 2026)

- Novo E2E com API/PostgreSQL sintéticos: criar rascunho incompleto ligado a uma refeição, alterar depois o nome da receita original, confirmar que o servidor devolve `base_changed=true`, reabrir o drawer e verificar aviso explícito «A receita base mudou desde este rascunho. Revê as escolhas antes de aplicar.».
- O teste confirma que o ato de retomar o rascunho desatualizado não altera o `recipe_id` da refeição. Não marcar uma revisão como conclusão sem nova confirmação do utilizador.
- Continua a ser permitida a **revisão manual** de um rascunho antigo; não o apagar automaticamente nem converter dados nutricionais ausentes em valores.
- Versão de interface **v2.0.7** (patch Z). Web/API/UX E2E só ficam aprovados quando verdes no SHA final; teste manual reservado para a próxima versão X/Y consolidada.

## Patch v2.0.8 — reutilização explícita de presenças no editor (19 novembro 2026)

- O formulário de **criação** de uma refeição apresenta, quando existe uma refeição anterior do mesmo tipo na semana atual, um seletor opcional para reutilizar apenas quem estava presente. Fontes limitadas a refeições `planned` anteriores da mesma semana/slot, usando a lista já carregada; o campo fica oculto quando não há fonte aplicável ou ao editar refeição já guardada.
- A operação de cópia não grava dados, não aplica quantidades/unidades da origem e não altera outros campos; é necessária a confirmação normal de «Guardar». O editor conserva o alerta de rascunho por guardar e a API mantém a validação de restrições ativas das pessoas selecionadas.
- `copyAttendanceSelection` tem teste unitário explícito com quantidades `emb`/`serving` e valores vazios, verificando a ausência de mutação da entrada. A regressão browser com duas pessoas fictícias verifica a cópia da seleção, a ausência de gravação antecipada, o destino após guardar e a preservação da refeição origem.
- A apresentação utiliza o tema e as larguras responsivas existentes. **Isto não constitui ainda um sistema de padrões persistentes/visitantes**; a expansão dessa função pertence ao marco funcional futuro, não a este patch.
- Versão visível **2.0.8**; validar os três CI no SHA final antes de declarar concluído o patch. Respeitar a cadência de patches Z sem novos testes manuais.

## Patch v2.0.9 — presenças por confirmar antes de gravar (19 novembro 2026)

- O editor manual distingue **Presente, Ausente e Por confirmar** para cada pessoa enquanto a refeição é criada. Por omissão, os participantes de uma nova refeição estão *por confirmar* — não são automaticamente tratados como ausentes. Ao abrir uma refeição já guardada, os presentes são recuperados do plano e os restantes membros da família aparecem como ausentes **apenas para efeitos de edição**, dado que o contrato de persistência atual contém só participantes.
- O botão de guardar é desativado enquanto existirem decisões por confirmar ou não houver ninguém presente. A lista enviada ao backend inclui **apenas** pessoas confirmadas como presentes; alterações individuais mantêm a validação de restrições pela API.
- «Selecionar todos/nenhum» e «Reutilizar presenças» são ações explícitas que resolvem a decisão de presença para os membros listados, sem mexer nas quantidades e unidades nem na refeição de origem. O aviso indica quantas decisões faltam.
- Testes Vitest cobrem estados e preservação de quantidades/unidades. E2E com PostgreSQL temporário verifica os estados iniciais, bloqueio da gravação prematura, reutilização de presenças, decisão individual e persistência depois de confirmar. **Não declarar aprovado até Web CI, API CI e UX E2E verdes no SHA final.**
- **Limite de modelo:** por confirmar é um estado do rascunho do editor, não é ainda um estado persistido de ausência na API. Para suportar padrões semanais guardados, convidados e exceções pendentes entre sessões será necessária modelação própria, migração segura e regras de autorização. Esta tarefa 11 permanece **parcial**. Não introduzir estados fictícios no registo clínico, nem inferir adequação nutricional.
- Versão visível **v2.0.9**, incremento Z sem pedir teste manual; preparar demonstração consolidada só quando os restantes blocos estiverem validados para X/Y.


## Patch v2.0.10 — decisões persistentes de presença por semana (19 novembro 2026)

- **Persistência sem nova migração:** o registo versionado `family_week_setups.settings` passa a conter, separadamente do campo `attendance` usado para gerar propostas, `attendance_decisions`: data, tipo de refeição e, por pessoa, `present`, `absent` ou `unconfirmed`. Não são inventadas presenças nem transformadas decisões pendentes em ausências.
- **Contrato API:** `WeekSetupWrite`/`WeekSetupRead` e `save_setup` validam datas dentro da semana, tipos de refeição selecionados, unicidade de decisões e pessoas pertencentes à família. Mantém controlo de concorrência via `expected_version`; gravação desatualizada devolve 409.
- **Compatibilidade:** cliente antigo que não envia `attendance_decisions` **não apaga** os estados já guardados. Um `attendance_decisions: []` explícito permite limpar. Os restantes campos do planeamento continuam a ser lidos e guardados.
- **Interface:** a secção expansível «Quem está em cada refeição?» do planeamento semanal inclui confirmações individuais, separadas dos checkboxes que definem quem entra numa proposta. As escolhas são guardadas quando se confirmam as opções da semana e regressam ao recarregar. Os valores podem ser reutilizados ao copiar a organização da semana anterior, com datas deslocadas sem alterar ingredientes, quantidades, refeições guardadas ou autorizações clínicas.
- **Testes:** Vitest valida o mapeamento entre semanas, opções explícitas e imutabilidade. E2E API/PostgreSQL sintético verifica gravação/releitura, transições de estado, conflito de versões, rejeição de datas inválidas e pessoas de outra família, compatibilidade com pedido de cliente antigo e ausência de alterações à refeição. E2E UI verifica seleção, gravação e recuperação no planeamento. **Não declarar os testes E2E aprovados enquanto o workflow do SHA final não concluir.**
- **Limites:** ainda não há **convidados sem perfil de pessoa** nem estados persistentes autónomos por refeição fora do planeamento semanal. A funcionalidade não modifica as regras de geração de propostas nem substitui confirmação de restrições. A tarefa 11 do checklist continua parcial. Patch Z `v2.0.10`: sem pedido de teste manual; manter PR #76 em draft e `main` intacta.

## Patch v2.0.11 — convidados sem perfil como previsão, não participante (19 novembro 2026)

- A API guarda `guest_notices` no planeamento semanal versionado existente: data, tipo de refeição e **contagem de 1–12 convidados** por slot. `0` na interface elimina a previsão do slot. Não existe conversão automática destes convidados em perfis familiares nem em participantes de refeições, porções, avaliação clínica ou compras.
- Valida unicidade de slot, pertença à semana escolhida e tipo de refeição ativo. A resposta de leitura mantém a contagem; pedidos de clientes antigos que omitirem o campo **não a apagam**, enquanto `guest_notices: []` limpa explicitamente. Mantém controlo de concorrência por versão do planeamento.
- A secção «Quem está em cada refeição?» apresenta campo numérico responsivo para os convidados e aviso explícito de que não são incluídos nas doses, avaliações nutricionais nem compras automáticas. Ao copiar organização da semana anterior, os convidados **não** são copiados por serem exceções pontuais.
- Vitest e E2E API/PostgreSQL temporário cobrem limites, duplicados, datas, isolamento de participantes e compatibilidade de cliente antigo; E2E UI verifica guardar e recuperar após reload sem reescrever a refeição original.
- **Limite de produto:** é uma **previsão de número de convidados**, não gestão completa de convidados com preferências, alergias, consentimento e perfil. Até haver informação individual confirmada, a aplicação deve continuar a apresentar adequação nutricional desconhecida para convidados; qualquer refeição destes deve ser revista manualmente. Não inferir segurança FODMAP.
- Versão **v2.0.11**, incremento Z. Web/API/E2E ainda requerem conclusão verde no SHA exato; não pedir teste manual, não fazer merge para `main` nem usar a base familiar real.

## Patch v2.0.12 — estabilização de foco do drawer (19 novembro 2026)

- Após sucesso dos três gates da v2.0.11 no SHA `a8a27210486ca900a38fb8baae8baabbf1a400f9`, a suite UX E2E concluiu com **19 cenários aprovados, mas 1 teste de foco do drawer precisou de retry** (run `44584110516`). Não confundir o resultado final verde com uma execução sem flakiness.
- Em `ContextDrawer.tsx`, a navegação Tab/Shift+Tab deixa de depender do foco nativo do browser para mover-se entre itens não extremos: todos os passos de Tab passam a calcular e focar explicitamente o próximo elemento visível/ativo no diálogo, com wrap entre o primeiro e o último. Escape e restauração de foco mantêm-se.
- O E2E existente verifica foco inicial, Shift+Tab, retorno ao botão de fecho, doze passos Tab sem fuga, Escape e retorno do foco à célula de refeição. Executar novamente Web/API/UX E2E no **SHA final da v2.0.12** e registar se o teste volta a requerer retry.
- A mudança é de acessibilidade/navegação, sem alteração de dados ou contratos e sem pedir teste manual na série Z.

## Patch v2.0.13 — contextualização de convidados e presenças no drawer (19 novembro 2026)

- O detalhe de refeição no `WeeklyProposalPreview` recebe os `guest_notices` e `attendance_decisions` da semana ativa, apenas quando a pessoa está no assistente de planeamento. O aviso é limitado **ao dia e tipo de refeição do drawer**; não transfere números de convidados ou decisões pendentes de outro slot.
- **Convidados sem perfil:** a contagem é só previsão; não participa nos cálculos nutricionais, nas doses, nas compras automáticas ou na validação de restrições. O drawer exige expressamente revisão manual.
- **Por confirmar:** mostra o número de decisões ainda abertas e informa que a seleção semanal **não altera automaticamente** participantes de uma refeição já guardada.
- Sem novo endpoint, migração ou alteração do motor nutricional; apenas integração de dados previamente persistidos e apresentação contextual.
- Testes Vitest novos verificam ausência de contaminação entre dias, tempos alimentares e setups inexistentes. Validar Web CI, API CI e UX E2E no SHA final. A cobertura browser específica deste aviso deve continuar no checklist antes da versão 2.1.0.
- Incremento Z: sem pedido de testes manuais, sem utilização da DB familiar real e sem merge na `main`.

## Patch v2.0.14 — proteção contra atualização obsoleta dos convidados (19 novembro 2026)

- Reforçado o cenário E2E API/PostgreSQL temporário de `guest_notices`: após um cliente antigo atualizar o planeamento sem apagar os convidados, uma escrita com `expected_version` obsoleta tenta alterar a contagem de 2 para 3 e deve devolver HTTP 409.
- O teste relê a API depois da rejeição para confirmar que a contagem original permanece inalterada; o cenário também preserva a verificação de limpeza explícita de convidados e de ausência de alterações nos participantes do plano.
- Não foram alterados modelos, endpoints, cálculos nutricionais, compras nem dados reais. Versão visível **v2.0.14** (Z): sem pedido de testes manuais. Validar Web CI, API CI e UX E2E no SHA exato e manter o PR #76 em draft.

## Patch v2.0.15 — roteiro de aceitação e reflow a 320 CSS px (19 novembro 2026)

- Criado `docs/ux/aceitacao-manual-v2.1.0.md` com cenários de aceitação para UX, família, restrições, receita/adaptação, semana, convidados, nutrição, compras, idiomas e proteção de dados; inclui matriz de resultados e gates para preparar o próximo Y.
- Incluído novo Playwright E2E com PostgreSQL sintético para testar drawer do plano semanal a **320 CSS px**, incluindo conteúdo da refeição, limites laterais, ausência de overflow horizontal e fecho do drawer.
- Este teste de reflow **não substitui** zoom real a 200%, que permanece no plano de aceitação.
- Versão de interface **2.0.15**, patch Z; não requer teste manual. Apenas declarar este incremento automaticamente validado quando Web CI, API CI e UX E2E terminarem verdes no SHA final. Não fazer merge.

## Patch v2.0.16 — rejeitar decisões semanais de presença duplicadas (19 novembro 2026)

- O E2E API/PostgreSQL sintético verifica agora que o planeamento rejeita com HTTP 422 duas entradas do mesmo dia/tempo em `attendance_decisions` e duas decisões contraditórias para a mesma pessoa no mesmo slot.
- Complementa o cenário já existente de isolamento por família, datas inválidas, concorrência por `expected_version`, compatibilidade de cliente antigo e preservação dos participantes de refeições guardadas.
- Trata-se de cobertura de regressão da validação existente, não de mudança no contrato, no motor de nutrição ou nos dados reais.
- Versão visível **v2.0.16** (patch Z); só considerar validado com Web CI, API CI e UX E2E verdes no SHA final. Continuar sem merge, sem pedir teste manual antes da v2.1.0.

## Patch v2.0.17 — convidados e presenças no drawer com navegador real (19 novembro 2026)

- Confirmado **Web CI, API CI e UX E2E verdes** no SHA da v2.0.16 `6fd21c8c7ef583610c75dfc95c4962b2a12686a8`.
- Adicionado Playwright E2E com API real e PostgreSQL sintético: criar segunda pessoa e configuração semanal com dois convidados e uma presença pendente; entrar no assistente, rever as restrições, abrir o detalhe do jantar na semana e verificar ambos os avisos no drawer.
- O teste fecha o drawer e consulta a API para garantir que a leitura do contexto **não alterou os participantes** nem a refeição guardada. Testes anteriores cobrem isolamento de dia/slot por função e persistência das decisões.
- A versão visível sobe para **v2.0.17** (Z). Teste novo ainda precisa de completar os workflows Web CI, API CI e UX E2E no **SHA final**; não tomar um código publicado como aprovação automática.
- Sem alteração de schema, regras nutricionais, clientes da família ou `main`. Continuar a preparar v2.1.0 com checklist `docs/ux/aceitacao-manual-v2.1.0.md`; só pedir testes manuais na minor consolidada.

## Patch v2.0.18 — acessibilidade e restauro do drawer após ciclos repetidos (19 novembro 2026)

- Novo cenário E2E Chromium com API e PostgreSQL sintéticos, em viewport 390 px e preferência `prefers-reduced-motion`: abrir e fechar três vezes o detalhe de uma refeição, confirmar `role=dialog`, `aria-modal=true` e nome acessível por `aria-labelledby`.
- Em cada ciclo, confirmar que o conteúdo principal fica `inert`, scroll corporal é bloqueado, Tab/Shift+Tab não escapam do modal e Escape fecha o drawer; depois confirmar que scroll e interatividade do fundo são restaurados, tal como o foco no botão da refeição original.
- Esta cobertura complementa os testes existentes de teclado e reflow. **Não equivale a auditoria WCAG completa nem substitui zoom real de browser a 200%**, ainda exigidos antes de v2.1.0.
- Frontend **v2.0.18** (patch Z). Apenas testes/documentação, sem migrações, sem alterações de API e sem acesso à família real. Aguardar Web CI, API CI e UX E2E verdes no SHA final antes de marcar como validado; PR #76 permanece draft.

## Patch v2.0.19 — ignorar elementos ocultos e desativados na navegação por teclado (19 novembro 2026)

- Os três gates **Web CI, API CI e UX E2E** foram confirmados com sucesso no SHA final de v2.0.18 `b9b1a1c0508af6c75bd840ad426c6ba7a3b2740d`.
- Em `ContextDrawer.tsx`, a lista de candidatos a foco ignora agora elementos efetivamente desativados (incluindo os que se encontram em `fieldset disabled`), ocultos por `visibility`, sob `aria-hidden=true` ou sob `inert`. Mantém Tab/Shift+Tab, Escape e restauro do foco.
- Playwright acrescenta um cenário sintético: injeta no DOM temporário um botão `visibility:hidden` e outro sob `fieldset disabled`, verifica que Shift+Tab passa para um elemento visível dentro do diálogo e que Escape continua a fechar.
- Versão de interface **v2.0.19** (Z). É uma correção de acessibilidade sem alteração de schema/API/dados. Verificar os três CI no SHA final e manter PR #76 em draft. Ainda falta auditoria real de zoom 200% antes da v2.1.0; não solicitar teste manual nesta patch.

## Patch v2.0.20 — conter foco programático no drawer (19 novembro 2026)

- Confirmado o sucesso de Web CI, API CI e UX E2E no SHA final da v2.0.19 `fed885d830d19b4796a28cadd2fe55cc71d145c5`.
- Em `ContextDrawer.tsx`, adicionada uma proteção `focusin` para devolver o foco ao botão de fecho se código externo ou atualizações dinâmicas tentarem colocar o foco fora do diálogo enquanto está aberto. O listener é removido antes de restaurar o foco original ao fechar, evitando reter foco após o unmount.
- Novo Playwright E2E, contra API/PostgreSQL sintéticos, cria um botão temporário fora de `#root` (logo, não protegido apenas por `inert`), tenta focá-lo diretamente e verifica que o foco regressa ao diálogo. Depois confirma fecho, retorno de foco e scroll libertado.
- Frontend **v2.0.20** (patch Z). Correção de acessibilidade sem alteração de schema/API/dados reais. Verificar os três CI no SHA final, manter PR #76 em draft e não pedir teste manual antes da v2.1.0.

## Patch v2.0.21 — regressão de layout do editor de ingredientes (19 novembro 2026)

- Confirmado o sucesso de Web CI, API CI e UX E2E no SHA final de v2.0.20 `8c1346b36d4a14625a17e54608a944034d7652b8`.
- Adicionado Playwright E2E com API/PostgreSQL sintéticos para abrir o editor de novo ingrediente em **320 e 390 CSS px**, nos temas claro e escuro, introduzir texto e verificar o estado de rascunho e visibilidade da ação de guardar.
- O teste verifica a ausência de overflow horizontal da página, confirmando que a interação pode decorrer sem deslocação horizontal; isto é regressão de reflow, **não** substitui zoom real a 200% nem auditoria visual integral.
- Frontend **v2.0.21**, patch Z; sem modificação de contratos/API ou dados da família real. Aguardar os três gates verdes no SHA final antes de marcar como validado; PR #76 mantém-se draft, sem solicitação de teste manual até v2.1.0.

## Patch v2.0.22 — editor de perfil responsivo e proteção de rascunhos (19 novembro 2026)

- Confirmado sucesso Web CI, API CI e UX E2E no SHA final de v2.0.21 `f07c9e28d84e7da09a91ab99816a4afd897f794c`.
- Adicionado cenário Playwright com API/PostgreSQL sintéticos para abrir o perfil de pessoa em 320 e 390 CSS px; verificar ausência de overflow horizontal, campo do nome e estado de alterações não guardadas.
- O teste verifica cancelamento de descarte (o rascunho permanece), confirmação de descarte (fecha o formulário) e leitura posterior dos membros da família para confirmar que a edição cancelada não alterou a pessoa original.
- Frontend **v2.0.22**, patch Z; sem alteração de API/schema, sem gravações nos dados familiares reais. Aguardar sucesso Web CI/API CI/UX E2E no último SHA, manter PR #76 draft e não pedir testes manuais antes da minor v2.1.0.

## Patch v2.0.23 — regressão de layout e descarte no formulário de saúde (19 novembro 2026)

- A última consulta ao CI de v2.0.22 mostrava Web CI e API CI aprovados e UX E2E ainda em execução; não declarar todos os gates verdes sem resultado observado no SHA exato.
- Adicionado cenário Playwright com API/PostgreSQL sintéticos para o formulário de condições de saúde em **320 px / tema claro** e **390 px / tema escuro**, verificando campos, rascunho e ausência de overflow horizontal da página e do formulário.
- O teste cancela uma primeira tentativa de descartar o rascunho (mantendo o conteúdo), confirma o descarte numa segunda tentativa e verifica que nenhuma condição fictícia foi guardada. Não introduz diagnóstico clínico nem altera os registos familiares reais.
- Versão de interface **v2.0.23** (Z). Teste e documentação não equivalem a validação: confirmar Web CI, API CI e UX E2E no SHA final; manter PR #76 em draft e `main` intacta. Zoom real 200% continua por verificar antes de v2.1.0.

## Patch v2.0.24 — restauro do contrato de navegação do protótipo aprovado (19 novembro 2026)

- Após alerta do utilizador sobre **aberturas duplas no mapa semanal e páginas em vez de drawers**, foi revista a referência `Casa_a_Mesa_Prototipo.html` e recuperada a prioridade do chat anterior. Auditoria e lista de desvios/pedidos preservados em `docs/ux/auditoria-fidelidade-prototipo-2026-11-19.md`.
- **Mapa semanal:** a callback `onEdit` do pai limpa a seleção do detalhe e URL antes de montar o editor, evitando dois `ContextDrawer` simultâneos; células vazias no mapa e no resumo do dia entram diretamente num só editor.
- **Casa:** receitas e ingredientes deixam de trocar toda a página pelo editor; o catálogo continua montado atrás de um `ContextDrawer`. Ações de guardar, duplicar, sair e proteção de rascunhos mantidas.
- **Pessoas:** vista de pessoa e criação passam a `ContextDrawer`, com a lista familiar estável no fundo e navegação direta de volta.
- Novo Playwright E2E verifica quantidade de diálogos igual a um, presença da página base e fecho direto nos percursos de semana, receitas, ingredientes e pessoa, com base de dados fictícia.
- Versão de interface **v2.0.24**. Ainda exige Web CI, API CI e UX E2E verdes **neste SHA final** e revisão do comportamento visual; não declarar prontidão da v2.1.0 ou efetuar merge.

## Patch v2.0.25 — corrigir recarregamento visual ao mudar de dia e fechar receitas (19 novembro 2026)

- O utilizador relatou que, ao selecionar outro dia da semana, surgia primeiro conteúdo vazio/carregamento e só depois o drawer correto; no catálogo de receitas a abertura/fecho provocava refresh e transições visualmente estranhas.
- **Causa identificada no código:** `FamilyMeals` reconstruía `request` quando `browsingDate` mudava, mesmo que o `startDate` da semana fosse idêntico, reativando `busy` e desmontando `WeeklyProposalPreview`. Agora a chave de pedido depende de `mode` e de uma `scopeDate` (segunda-feira comum a todos os dias da mesma semana). Mudar data no URL continua a selecionar o dia, mas **não refaz o pedido da mesma semana**. Mudar efetivamente de semana continua a carregar dados novos. `editing` já não é limpo ao mudar apenas a data.
- **Receitas e ingredientes:** removida a dependência dos pedidos de catálogo em `selected`. Abrir e fechar drawer não dispara consultas; guardar aumenta `revision` e recarrega informação. Durante atualização, os cartões antigos permanecem montados até à resposta, em vez de trocar a lista por um spinner.
- Adicionados cenários Playwright de seleção consecutiva de dias com uma única grelha montada e sem novo GET de plano semanal, mais abertura/fecho de receita duas vezes sem novo GET de lista de receitas.
- Versão de interface **v2.0.25**. Manter PR #76 em draft e `main` intacta. A correção não está automaticamente validada: exigir Web CI, API CI e UX E2E verdes **neste SHA**, e confirmar que os testes de transição não introduzem comportamento secundário.

## Patch v2.0.26 — cancelar editor não recarrega plano (19 novembro 2026)

- Confirmado sucesso **Web CI, API CI e UX E2E** no SHA final de v2.0.25 `630d56b0337820f1d7c182485224d3d1c535b826`. O utilizador confirmou que o comportamento de abrir/fechar drawers ficou bom.
- Ao fechar sem gravar ou apenas consultar a edição de refeição, `MealEditForm` chama `onDone(false)`; a callback do pai desmonta somente o drawer, **sem refazer GET nem substituir a grelha semanal por loading**.
- Após guardar/criar/remover com êxito, a callback chama `onDone(true)` e continua a executar `refreshPlan`, preservando a consistência dos dados. A proteção de alterações não guardadas permanece ativa.
- Novo Playwright E2E com PostgreSQL sintético verifica fecho por Escape de um editor existente, uma única modal, preservação da grelha e zero pedidos GET de plano após cancelamento.
- Prioridades seguintes e release gates documentadas em `docs/ux/roadmap-v2.1.0-rc.md`.
- Frontend **v2.0.26**, patch Z; exigir Web/API/UX E2E verdes no SHA final antes de marcar como validado. PR #76 continua draft; `main` e dados reais intactos.

## Patch v2.0.27 — gestão do stock da despensa num único drawer (19 novembro 2026)

- Após publicação de v2.0.26 `0c0390e52519579cfa370fd6c4be230d3b1bf64c`, Web CI e API CI passaram; UX E2E ainda estava em execução na última consulta, logo não há aprovação completa confirmada.
- **Despensa:** criar e editar lotes deixa de apresentar um formulário inline que desloca a lista. A página de stock permanece montada; `ContextDrawer` apresenta o editor, fecha diretamente para a lista e conserva as ações de stock existentes.
- Novo controlo de rascunho compara os valores atuais com a fotografia inicial; fechar ou navegar com alterações exige confirmação e preserva o editor se for recusada. Bloqueio de unload de dados não guardados.
- Playwright com dados fictícios/PostgreSQL temporário abre o stock em mobile 390px, verifica que há **um único drawer** e que a lista continua montada, faz uma edição e exercita recusa e aceitação de descarte sem persistência de lote.
- Interface passa a **v2.0.27**, patch Z; exigir Web CI, API CI e UX E2E verdes no SHA final. Nenhuma alteração de API/schema, `main` intacta, PR #76 em draft. Ainda não pedir testes manuais antes da minor v2.1.0.

## Patch v2.0.28 — editor de artigos de compras em drawer (19 novembro 2026)

- Na consulta ao SHA v2.0.27 `9342f7232dc9b85d25894c8a987dd1581c38e8bc`, Web CI e API CI passaram. UX E2E foi **cancelado após novos commits**, não considerado aprovado. A validação passa a ser exigida no SHA final de v2.0.28.
- **Compras:** editar um artigo deixa de apresentar um formulário inline que desloca a lista; passa a um único `ContextDrawer`, mantendo artigos, filtros e contexto de compras montados no fundo.
- Um rascunho com nome, quantidade ou unidade alterados exige confirmação ao fechar/navegar. Recusar mantém o formulário; aceitar fecha sem persistir. Guardar usa o contrato API existente e atualiza o artigo, distinguindo alteração de artigo de receção de stock.
- Playwright com PostgreSQL sintético cria um artigo manual fictício, abre edição em 390px, verifica que só existe um diálogo e a lista permanece; recusa/aceita descarte e, na segunda abertura, confirma a alteração persistida.
- Interface **v2.0.28**, patch Z; sem API/schema novos nem alterações na `main`. Confirmar sucesso Web CI, API CI e UX E2E **no mesmo SHA final**, manter PR #76 draft e não pedir teste manual antes da v2.1.0.

## Patch v2.0.29 — corrigir overshoot do drawer a 320px (20 novembro 2026)

- A v2.0.28 no SHA `620aa0a21e64fa82fed7900ab7e82888582dddfc` passou Web CI e API CI e passou o novo E2E de compras e o E2E de despensa, **mas falhou o gate UX E2E** no teste existente `narrow viewport: weekly drawer reflows at 320 CSS px without horizontal scrolling` (limite 321px, posição direita observada 321,281px, retry 321,282px). Não declarar v2.0.28 aprovada.
- O CSS de abertura do drawer usava `var(--motion-ease)`, cujo easing permite overshoot transitório; a animação foi trocada para `ease-out` monotónico sem ultrapassar o ponto final, preservando o movimento e `prefers-reduced-motion`.
- Frontend **v2.0.29** (patch Z). Usar o E2E existente a 320px como gate da correção; a aprovação requer Web CI, API CI e UX E2E verdes **no mesmo SHA final**. Sem alteração de API/schema, dados reais ou `main`, PR #76 mantém-se draft.

## Patch v2.0.30 — estabilizar data do mapa mobile e largura do drawer (20 novembro 2026)

- No SHA final v2.0.29 `e3e23912658faaf1d64885dbf9f4ac3931149b89`, Web CI e API CI passaram, mas UX E2E **falhou** (3 testes). Falhas reais: a translação animada do drawer excedeu a largura a 320 CSS px, e os testes de acessibilidade não encontraram a refeição na grelha mobile quando a data da execução passou de 19 para 20/11.
- **Correção de produto 1:** removida a translação `translateX` da animação de entrada do `ContextDrawer`; permanece um fade progressivo e o movimento reduzido continua desativar animações. O painel deixa de poder sair do viewport durante a abertura.
- **Correção de produto 2:** `WeeklyProposalPreview` recebe agora `initialDate` independentemente de `initialSelection` (que só existe quando uma refeição concreta está selecionada). O mapa mobile respeita a data explícita do URL, em vez de a substituir pelo dia atual; o drawer não abre apenas por existir data.
- Adicionado E2E sintético de rota `/#/meals?date=2026-11-19&mode=week` a 390px, que verifica quinta-feira selecionada, refeição datada visível, e ausência de drawer automático. Os três testes de acessibilidade/reflow que falharam mantêm-se ativos como regressões obrigatórias.
- Frontend **v2.0.30**, patch Z; exigir Web CI, API CI e UX E2E verdes **neste SHA final** antes de continuar para novas funcionalidades. Sem merge, API/schema ou dados familiares reais.

## Patch v2.0.31 — substituições por receita em drawer, fontes FODMAP preservadas (20 novembro 2026)

- **Baseline validada:** a v2.0.30 no SHA `277e87f898064919fd95e361fe59e085797debe8` obteve os três gates verdes (Web CI, API CI e UX E2E sintético).
- **Casa → Mais ferramentas → Substituições:** na revisão não vinculada a uma refeição específica, clicar numa receita abre **um único `ContextDrawer`** e mantém a lista de receitas/filtro montados no fundo. O primeiro item deixa de ser expandido automaticamente quando o utilizador abre o separador.
- A revisão de uma receita já fixada pelo contexto (`recipeId` explícito, por exemplo num fluxo de adaptação) **continua inline** no contexto existente, sem empilhar drawers.
- A componente continua a apresentar claramente que a adequação FODMAP **não foi avaliada por porção**; as fontes educativas não equivalem a aprovação clínica. Registos de substituições, edição de variantes, dados nutricionais e escolhas de receitas não foram removidos.
- Acrescentado E2E sintético mobile 390px: nenhuma modal ao abrir a lista, uma única modal depois de escolher uma receita, detalhe FODMAP com incerteza, fechar diretamente para a lista e consultar as fontes separadamente.
- Versão de interface **v2.0.31**. Exigir Web CI/API CI/UX E2E verdes no SHA final antes de marcar como validada; PR #76 permanece draft; `main` e dados reais intactos.

## Patch v2.0.32 — títulos de substituições e distinção entre gosto e adequação (20 novembro 2026)

- A v2.0.31 SHA `f19274821a4342ee0bd7ad40fe04d48c178e7d98` teve Web CI e API CI aprovados; UX E2E **falhou num único cenário**, devido ao título da receita duplicado no drawer, detetado pelo Playwright em strict mode. Os restantes cenários passaram.
- **Substituições:** removido cabeçalho duplicado no drawer de revisão; o título permanece único e acessível. Na revisão vinculada por `recipeId` o cabeçalho local continua disponível.
- **Preferências de receitas:** a média familiar é agora identificada explicitamente como **avaliação de gosto**, não score de segurança, FODMAP ou nutrição; estrelas e «Não gosto» apresentam estado `aria-pressed`, sem alterar a regra de elegibilidade.
- Novo cenário API sintético testa avaliações de dois membros (5 e 1 estrelas), cálculo da média 3, eliminação de uma avaliação, média 5 com apenas um membro e integridade da receita original.
- Frontend **v2.0.32**. Exigir Web/API/UX E2E verdes **no SHA final**, não declarar a v2.0.31 validada; PR #76 draft, `main` e dados reais intactos.

## Patch v2.0.33 — cobertura nutricional individual e proveniência das regras (20 novembro 2026)

- **Baseline:** a v2.0.32 no SHA `b39005f478865a8a3f24d5b89aab146edae24474` passou Web CI, API CI e UX E2E no mesmo commit.
- **Pessoa → Nutrição → Adequação ao plano:** após avaliar uma receita/porção, o painel apresenta contagens distintas de regras efetivamente avaliadas, regras sem evidência suficiente, orientações profissionais ainda não avaliadas e bloqueios obrigatórios identificados. As contagens são derivadas **apenas** dos estados devolvidos pela API; não simulam avaliação clínica.
- Cada regra/orientação permite expandir as **fontes efetivamente registadas** (título de plano, nome de origem e referência, quando disponíveis); se faltarem, a interface identifica essa ausência em vez de inferir fontes.
- Mantidos elegibilidade do motor, estado do plano profissional, valores observados, projeções diárias, conflitos, melhoria e transformação. Nenhuma alteração na avaliação API, no esquema, nos planos reais ou na classificação FODMAP.
- Novos testes unitários de ausência de evidência, bloqueios obrigatórios e proveniência explícita, além de layout responsivo de cobertura.
- Versão de interface **v2.0.33** (Z). É necessário confirmar Web CI, API CI e UX E2E verdes neste SHA final; PR #76 draft, `main` e dados familiares reais intactos.

## Patch v2.0.34 — proveniência e incerteza de condições individuais (20 novembro 2026)

- **Baseline validada:** a v2.0.33 no SHA `c5fc2e4432deb933016fcc7b426f00b3759129e0` passou Web CI, API CI e UX E2E no mesmo commit.
- **Pessoas → Saúde:** cada condição mostra agora, separadamente, a referência da origem, o início e o fim conhecidos; falta de informação é **desconhecido/não indicado**, não ausência de doença ou aprovação.
- Ao existir estado `confirmed` com origem do utilizador ou referência ausente, o ecrã assinala que a confirmação profissional **não pode ser verificada ali**. Mesmo com fonte preenchida, a app não certifica diagnósticos; registar condição não cria automaticamente uma restrição alimentar, receita ou prescrição.
- Introduzido `conditionEvidenceSummary` com testes unitários de datas desconhecidas, dados de fonte, confirmação declarada e referência insuficiente; layout responsive da evidência.
- **Frontend v2.0.34**, patch Z; sem alteração na API/schema ou nos dados reais. Exigir Web CI/API CI/UX E2E verdes no SHA final; PR #76 mantém-se draft, `main` intacta e nenhuma solicitação de teste manual antes de v2.1.0.

## Lote consecutivo v2.0.35–v2.0.37 — porções, proveniência e consistência assíncrona (20 novembro 2026)

**Base verificada:** v2.0.34 SHA `aee0e83763f2ee9ffb0909bda40390fd7152bf87` com **Web CI, API CI e UX E2E verdes**.

### v2.0.35 — composição da porção realmente avaliada
- Em Pessoa → Nutrição → Adequação ao plano, o resultado mostra energia e nutrientes devolvidos pela API para a **porção selecionada**, e não valores de receita integral inferidos ou uma receita genérica.
- Energia desconhecida é apresentada como desconhecida, **nunca 0 kcal**. Nutrientes não devolvidos não são apresentados como zeros; valores não numéricos são filtrados da grelha.
- `planFitCandidateNutrition` com regressão unitária para energia e nutrientes em falta; layout responsive em `meal-plan-fit.css`.
- Frontend marcado v2.0.35; marco intermédio, sem validação independente no SHA final após patches posteriores.

### v2.0.36 — metadados de plano profissional
- `NutritionPlanAuthorityCard` apresenta referência documental e número da versão de cada plano ativo, com indicação de referência ausente.
- Aviso claro: declarar um profissional ou uma origem no registo **não equivale a verificar credenciais ou autenticidade**. Validade e cobertura por refeição continuam independentes.
- `nutritionPlanProvenance` + testes unitários de fonte ausente, referência fornecida e data final opcional. Sem novo esquema, sem alterações de elegibilidade.
- Frontend marcado v2.0.36; marco intermédio, sem validação independente no SHA final após patches posteriores.

### v2.0.37 — descartar resultados assíncronos de contexto anterior
- `MealPlanFitPanel` invalida respostas pendentes sempre que mudam pessoa, data, estado nutricional do dia, refeição, receita ou quantidade. A avaliação usa contador de geração para aceitar **só a resposta do contexto atual**.
- A geração de propostas de transformação usa contador independente, invalidado ao iniciar outra avaliação ou ao alterar qualquer parâmetro. `finally` e erros de pedidos anteriores não alteram a UI atual.
- Evita resultados e propostas de adaptação desfasados de seleção/porção; o backend e a persistência não mudaram.
- Frontend marcado v2.0.37. **Gate final obrigatório:** Web CI, API CI e UX E2E verdes no mesmo SHA deste lote. Continuar PR #76 draft, `main` e base familiar real intactos.

**Limites:** ainda falta teste browser específico para respostas deliberadamente atrasadas, visualização ao zoom 200% e revisão transversal de restrições/tolerâncias face a fontes clínicas. Não declarar v2.1.0 pronta só com estes patches.

## Correção durante validação do lote 2.0.35–2.0.37 (20 novembro 2026)

- No SHA `ee778989f56d897a5a9cec2865a1c64ab857f21c`, o Web CI falhou por **TypeScript TS2352 num fixture parcial** dos testes da composição da porção (cast direto de objeto parcial para `MealPlanFitResult`).
- Corrigido o teste com cast explícito `unknown`, mantendo a tipagem de produção; a apresentação nutricional passa ainda a tratar strings vazias como **dados desconhecidos**, e não zero. Teste adicional para esse caso.
- Publicados commits corretivos `8aa8208`, `33eeae5` e `cefae3d`. **Não marcar a entrega como aprovada** sem os três gates verdes no último SHA.

## Entrega agrupada v2.0.38–v2.0.39 — avaliação nutricional a partir da refeição da pessoa (20 novembro 2026)

- **Baseline:** v2.0.37 SHA `bab5ef8ae0928f45ca6c87d55533bc028eeef6aa` com **Web CI, API CI e UX E2E aprovados no mesmo SHA**.
- **v2.0.38 — atalho de contexto:** em Pessoas → Visão geral → Refeições de hoje, cada refeição com tipo reconhecido passa a ter `Avaliar porção no plano`. Abre diretamente a secção Nutrição **da mesma pessoa**, sem segundo drawer, preservando o separador de pessoa e selecionando o tipo de refeição correspondente (pequeno-almoço/almoço/lanche/jantar). Apenas refeições em que participa têm atalho.
- **v2.0.39 — escolha explícita e limpar contexto:** o título do plano/da refeição não é usado para adivinhar uma receita. A avaliação contextual começa **sem receita escolhida**, com seletor explícito e botão Avaliar desativado até existir receita/porção utilizável. O contexto mostra uma nota de que o utilizador tem de escolher receita e confirmar quantidade. Mudar de refeição remonta o avaliador para descartar resultados anteriores; `Limpar seleção` regressa ao avaliador genérico sem sair do perfil.
- Teste Playwright com PostgreSQL sintético cria refeição no dia devolvido pela API do dashboard e verifica atalho mobile, seleção do jantar, ausência de receita implicitamente escolhida, desativação da avaliação sem receita e limpeza sem drawer adicional.
- **Frontend v2.0.39** (versões 2.0.38 e 2.0.39 agrupadas num lote). Gates Web CI, API CI e UX E2E obrigatórios **no SHA final**. Sem API/schema alterados, `main` intacta, PR #76 draft, dados reais intocados. Ainda sem pedido de testes manuais até v2.1.0.

## CI de confirmação v2.0.39 — 20/11/2026

- **Código + documentação** no SHA `55c0626cbc97aeab71b35debc6f2379491519a44`: **Web CI, API CI e UX E2E sintético concluídos com sucesso (3/3)**. O teste de atalho contextual de refeição passou.
- PR #76 permanece draft; não foi feito merge, não foram modificados dados reais nem solicitados testes manuais. O próximo checkpoint continua a ser a candidata v2.1.0.

## Entrega agrupada v2.0.40–v2.0.42 — coerência temporal e validade de avaliação (20 novembro 2026)

- **Baseline validada:** v2.0.39 SHA `7dbf328cb42a0b777fc5caa648dcd30501068aa7`: Web CI, API CI e UX E2E **verdes no mesmo commit**.
- **v2.0.40 — data e fuso horário:** `PersonOverview` deixa de obter estado nutricional com `new Date().toISOString()` e passa a usar **meio-dia local no dia do dashboard**, com offset explícito de `Intl.DateTimeFormat(timeZoneName: shortOffset)`. Evita consultar um dia UTC que não corresponda ao dia em que a pessoa está a analisar refeições.
- **v2.0.41 — rejeição de contexto incompatível:** apenas usar `daily_nutrition_state` quando tanto a resposta `planning_date` como o campo `state_date` correspondem exatamente ao dia do dashboard. Dados ausentes/dia diferente não são misturados; pessoa, perfil e estado antigo são limpos quando muda o contexto. `planningDateInstant` rejeita datas impossíveis.
- **v2.0.42 — plano atualizado invalida avaliação anterior:** importar/ativar um plano profissional incrementa `planAuthorityRevision` e remonta o avaliador da pessoa, removendo resultados calculados sob o plano anterior, sem interferir na UI de outros membros. Teste E2E verifica que o pedido de bootstrap usa a data do dashboard; testes Vitest cobrem Lisboa inverno/verão, fuso de meia hora, fuso +13, contexto de dia errado e estado inexistente.
- Frontend **2.0.42** — lote de três incrementos, sem validação CI separada de cada número intermédio. Requer Web CI, API CI, UX E2E verdes **no SHA final** antes de ser considerado aprovado.
- PR #76 draft; `main`, dados pessoais, schema e API de produção intactos. Continuar sem testes manuais até candidato v2.1.0.

## Entrega agrupada v2.0.43–v2.0.45 — respostas tardias, validação do contexto e confiança nutricional (20 novembro 2026)

- **Baseline:** v2.0.42 SHA `985d21c4cea6749fd92c1b4730bcd50d6e6ecaae` teve Web CI, API CI e UX E2E **3/3 aprovados**.
- **v2.0.43 — regressão de resposta tardia:** novo Playwright com PostgreSQL sintético e composição de receita **apenas simulada em HTTP**. Interceta `POST /meal-plan-fit`, atrasa deliberadamente a resposta, altera a porção e verifica que o resultado antigo não aparece, sem afetar dados reais. O teste espera a entrega efetiva da resposta.
- **v2.0.44 — validação do contrato de resposta:** `planFitMatchesRequest` compara pessoa, dia, tipo de refeição e quantidade numérica da resposta contra o pedido que originou a avaliação. Mesmo um HTTP 200 para outro contexto é rejeitado com explicação localizada PT/EN, em vez de mostrar uma pontuação incorreta. Testes unitários verificam diferenças e quantidades vazias.
- **v2.0.45 — resultados provisórios:** a pontuação ganha nota explícita de **evidência incompleta/não certificação** quando há regras desconhecidas, orientações não avaliadas, plano ausente/parcial/conflituoso ou zero regras avaliadas. `planFitHasOpenEvidence` e testes unitários, acessibilidade e CSS neutro responsivo.
- O resultado mantém a decisão/score do backend como fornecido, sem calcular ou inventar segurança FODMAP, nutrição ou validação clínica. Interface **v2.0.45**; versões intermédias agrupadas, sem provas CI separadas.
- **Obrigatório:** Web CI, API CI e UX E2E verdes **no SHA final**. PR #76 draft, `main` e dados familiares reais intactos. Sem solicitação de teste manual até v2.1.0.

## Correção v2.0.46 — E2E revelou resposta nutricional desatualizada após editar porção (20 novembro 2026)

- No SHA `2b3b2dc5bfdf5844667ec8957733853d40fb3ad9`, **Web CI e API CI passaram** e UX E2E **falhou num cenário novo**, `nutrition: late fit response cannot overwrite a changed portion`, em ambas as tentativas. Os outros 38 testes passaram.
- A causa foi confirmada no código: o `onChange` da quantidade apagava o resultado visível mas **não incrementava o contador de invalidação**. Assim, uma avaliação HTTP antiga completada após a edição voltava a mostrar a porção anterior.
- Em v2.0.46, o `onChange` da quantidade passa a chamar `invalidateEvaluation()` para cancelar logicamente tanto a avaliação como propostas de adaptação pendentes. Mantém-se o teste Playwright com HTTP deliberadamente atrasado, sem afrouxar a asserção.
- Versão web **2.0.46**; exigir Web/API/UX E2E verdes **no mesmo SHA final**, PR #76 draft, `main` intacta. A v2.0.45 não passou 3/3 e não deve ser indicada como validada.

## Fecho de validação v2.0.46 — 20/11/2026

- **SHA `a411eb9162deb93054a81eed7bf14ace6e05d00a`: Web CI, API CI e UX E2E sintético concluídos com sucesso (3/3).** O E2E novo de resposta tardia após alterar a porção passou sem enfraquecer a asserção.
- A correção v2.0.46 permanece no PR #76 draft; `main` intacta. Esta validação não substitui a auditoria visual, o zoom 200% nem a aceitação manual previstos para v2.1.0.

## Lote consecutivo v2.0.47–v2.0.49 — reflow, quantidade segura e idiomas (20 novembro 2026)

- **Baseline validada:** v2.0.46 no SHA `6355d48db5583ad5d8bf68c8949ce9c4c8496d89` passou Web CI/API CI/UX E2E no mesmo commit.
- **v2.0.47 — reflow equivalente a zoom 200%:** novo Playwright sintético testa o drawer no viewport CSS de 640px (largura equivalente a uma janela desktop de 1280px sob zoom real a 200%, **sem afirmar que o browser foi aumentado realmente**) e no viewport 320×550; verifica ausência de overflow horizontal, cabeçalho, controlo Fechar visível, região de conteúdo rolável, Escape e restauro do foco. Ajustados CSS da altura reduzida e `:focus-visible` do Fechar. A verdadeira inspeção com zoom do browser a 200% **permanece pendente** na checklist.
- **v2.0.48 — validação de quantidade da avaliação:** quantidade 0, negativa, vazia ou inválida não pode iniciar avaliação; valores inválidos preenchidos recebem `aria-invalid` e mensagem `aria-describedby` localizada PT/EN. A resposta continua vinculada à quantidade selecionada, nunca assumindo dados em falta como zero. Regressão E2E sintética de -1 e zero integrada no teste de resposta tardia.
- **v2.0.49 — percurso multilingue/tema:** novo Playwright em mobile muda PT→EN e tema escuro, abre o perfil de pessoa em um só drawer, percorre Nutrição e Saúde, fecha com Escape e confirma preferência após reload. Ajustado o helper de testes para não sobrepor escolha de idioma em cada reload; não muda o comportamento de produção.
- Frontend **v2.0.49**, lote de três patches (sem CI independente dos marcadores intermédios). **Exigir Web CI/API CI/UX E2E verdes no SHA final.** Sem schema/API alterados, PR #76 draft, `main` e dados familiares reais intactos.

## Entrega agrupada v2.0.50–v2.0.52 — propostas e respostas coerentes com a porção (20 novembro 2026)

- **Baseline:** v2.0.49, SHA `d122a2bc6e1e7f7c90ab0a0fcf1b463c44228792`: Web CI/API CI/UX E2E **3/3 aprovados**.
- **v2.0.50:** a resposta de `meal-transformations/proposals` só é apresentada quando identifica a mesma pessoa, receita original, data, tipo de refeição e quantidade da avaliação. A função `transformationMatchesRequest` verifica também o `baseline_fit`; respostas HTTP 200 para outro contexto são recusadas com erro PT/EN, não convertidas em adaptações aceites. Teste unitário de resposta de outra receita/pessoa/porção.
- **v2.0.51:** uma nova avaliação apaga a pontuação antiga e o estado de espera de propostas já invalidadas. Alterar a porção/receita/dia limpa avisos anteriores; evita o botão «Sugerir melhoria» preso em carregamento depois de avaliar novamente. Novo E2E sintético de resposta HTTP 200 pertencente a outra pessoa garante alerta e ausência de resultados visíveis.
- **v2.0.52:** validação da unidade da porção na resposta (`g` vs `serving`), além do valor numérico: a mesma quantidade com unidade diferente não passa a verificação de contexto. Testes unitários da avaliação e do `baseline_fit` das transformações.
- Frontend **2.0.52**, três patches Z agrupados, sem prova CI independente das versões intermédias. Obrigatório: **Web CI, API CI e UX E2E verdes no SHA final**.
- PR #76 mantém-se draft, `main` intacta; apenas dados sintéticos e HTTP simulado nos testes, sem mudanças de API/schema nem certificação nutricional/FODMAP inventada.

## Fecho de validação v2.0.52 — 20/11/2026

- **Código e documentação no SHA `3833c18fa8284299ef964607889784a7a58c1ff2`: Web CI, API CI e UX E2E sintético concluídos com sucesso (3/3).** Inclui os novos testes de respostas HTTP 200 de outra pessoa, validação do contrato de transformações e unidade/quantidade.
- Os três gates aprovam o código do lote; continua pendente a inspeção visual real, zoom 200% e aceitação manual para a candidata v2.1.0. PR #76 mantém-se draft, sem merge ou acesso a dados familiares reais.

## Entrega agrupada v2.0.53–v2.0.55 — acessibilidade real dos drawers (20 novembro 2026)

- **Baseline:** v2.0.52, SHA `d06f402a9bfb398084ef91e26a46da09cfb79b6c`, obteve **Web CI, API CI e UX E2E sintético verdes (3/3)**.
- **v2.0.53 — navegação em disclosures:** o ciclo de Tab/Shift+Tab de `ContextDrawer` passa a incluir `<summary>` de secções `<details>` e campos `contenteditable`, que antes podiam ser omitidos do foco apesar de serem controles nativos. E2E com `details` sintético aberto/fechado confirma Summary → botão expandido → Summary e wrap ao Fechar.
- **v2.0.54 — restauro de foco resiliente:** ao fechar um drawer cujo elemento invocador já desapareceu por filtro/atualização, o foco regressa à navegação primária ativa ou à marca, em vez de ficar perdido no `body`. A manutenção habitual de foco sobre invocadores existentes permanece inalterada. E2E simula remoção sintética do botão invocador sem persistir alterações na base.
- **v2.0.55 — alvo de interação e foco visível:** botão Fechar passa a 44×44 CSS px, com `touch-action: manipulation`; `summary:focus-visible` recebe contorno explícito. Regressão de reflow já existente a 640 CSS px e 320×550 confirma a dimensão do alvo, sem scroll horizontal ou cabeçalho cortado.
- Frontend **v2.0.55**, três incrementos Z agrupados, sem CI independente para os marcadores intermédios. Exigir **Web CI/API CI/UX E2E verdes no SHA final**.
- A auditoria com zoom **real** do browser, tecnologia de assistência e comparação visual com protótipo continua **pendente** e não pode ser inferida destes testes. PR #76 draft; `main`, API/schema e dados familiares reais não foram alterados.

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

## Patch v2.0.64 — overlay claro a partir do HTML aprovado (20/11/2026)

- Corrigida apenas a transparência/cor da cortina por trás do drawer no tema claro: o protótipo original especifica `#0d1d184d`; a aplicação usava mistura de cor dependente do token do fundo.
- v2.0.63 (overlay escuro) tinha os três gates CI verdes no SHA `7d9d54bb06b87dd854a5857c71e6d311029eae31`. Para v2.0.64, conferir os três gates no commit final; não declarar equivalência visual nem pedir teste manual antecipado.
- Não foram modificados endpoints, rotas, state React, lógica de nutrição, API, DB ou `main`.

## Patch v2.0.65 — hierarquia contextual do título (20/11/2026)

- Reposição no `ContextDrawer` da hierarquia de cabeçalho do protótipo: legenda discreta NutriFlow AI · Casa à Mesa acima do título, alinhamento com área de fecho e estilo independente do conteúdo. `aria-labelledby` continua a apontar apenas para o título específico, evitando repetição decorativa para leitores de ecrã.
- Sem alterações de callbacks, dados ou geometria do modal; a regra do foco e o botão de 44 px permanecem como em v2.0.62. CI Web/API/UX E2E e auditoria visual ainda precisam de confirmação no SHA desta versão.

## Correção v2.0.66 — identidade da aplicação (20/11/2026)

- A decisão já implementada em `apps/web/src/ui/Brand.tsx` mantém-se: **NutriFlow AI** (nome), **Casa à Mesa** (subtítulo) e **v${APP_VERSION}** (versão de `apps/web/package.json`). Não criar marcas paralelas nos drawers.
- Revertida a legenda «NutriFlow AI · Casa à Mesa» introduzida incorretamente nos cabeçalhos do `ContextDrawer` na v2.0.65. O drawer conserva só o título da operação e os comportamentos existentes de foco/fecho. Mantidos os ajustes dos overlays claro e escuro das v2.0.63–64.
- Patch só frontend e documentação, sem alterações de API, base de dados ou `main`. CI Web/API/UX E2E no SHA final ainda por verificar.
