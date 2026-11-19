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
