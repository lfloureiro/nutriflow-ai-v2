> Referência de continuidade: [estado atual e próximas tarefas](../handoff-2026-11-19.md). Registos intermédios abaixo são históricos; o fluxo atual está em aceitar-trocas-e-refeicao.md.

# Cross-check da app real com o protótipo aprovado

18 novembro 2026 · preview local `codex/ux-foundation-preview`. Referência: `Casa_a_Mesa_Prototipo.html` e fontes `casa-a-mesa-v4`, lidas sem alteração. Comparação visual em Edge headless, sem capturar nem controlar o ecrã do utilizador. Não é uma declaração de equivalência funcional completa.

## Resultado desta comparação

A identidade e a home seguem a direção aprovada. A semana anterior tinha texto excessivo por célula e linhas desalinhadas. O novo incremento aproxima a hierarquia e a densidade do protótipo: sete dias, quatro linhas alinhadas, estado curto por célula e detalhe progressivo. No mobile há seleção explícita de um dia, sem comprimir sete colunas.

| Área | Cross-check e alteração | Limite que permanece |
|---|---|---|
| Marca e paletas | NutriFlow AI / Casa à Mesa; claro marfim/verde e escuro carvão/âmbar; seletores diretos | Auditoria completa de contraste/teclado de todos os ecrãs pendente |
| Home | Mantém refeição atual, família e quatro tempos; atalhos receitas/compras aproximam os cartões de ação do protótipo; foco horário real | Ainda falta abrir diretamente a refeição da home no detalhe selecionado |
| Semana desktop | Linhas alinhadas com subgrid, vazios tracejados acionáveis, resumo de tempos guardados e vazios | Ainda não é o painel lateral/drawer do protótipo: detalhe progressivo abaixo do mapa, com foco/retorno |
| Semana mobile | Seletor de sete dias, apenas quatro tempos do dia escolhido, botões de modo visíveis | Teste de usabilidade com pessoas e dispositivos reais pendente |
| Estado das trocas | Célula resume: trocas por rever / adaptação em proposta / aplicada | Sugestão não é prova de conflito obrigatório nem de adequação |
| Detalhe/adaptação | Pessoas presentes com avatares; base e alternativa com quantidades, motivo, estado e fontes em detalhe | Aceitação de variantes continua no fluxo existente de autoria/validação/ativação; não há botão fictício de aplicação parcial |
| Quantidades | Receita inteira e porção individual explicitamente distintas; falta de quantidade aparece como desconhecida | Avaliação FODMAP por dose depende de evidência e validação do servidor |
| Contexto | Abrir espaço vazio leva ao editor real; cancelar regressa ao mesmo dia e tempo; botão volta ao mapa | Roteamento por URL/deep-link continua pendente |
| Fluidez | Fontes de restaurante/entrega só montam ao expandir; restrições são atualizadas antes das ações do contexto | Não representa certificação de performance global |
| Receitas/família | Cartões, avaliações no detalhe, criação progressiva e avatares consistentes preservados | Editor de ingredientes e compras/despensa ainda precisam da mesma revisão de densidade |
| IA/ML/NLP | Regras, evidência, ranking e propostas existentes permanecem no servidor | Este lote é UX; não implementa treino de um novo modelo, embeddings ou parser NLP |

## Verificação executada

- 160 testes frontend passaram; TypeScript/build verificados após as alterações.
- Navegador: 28 espaços, alinhamento das quatro linhas entre sete dias, resumo de ocupação, editor real e cancelamento com contexto preservado, comparação base/alternativa e regresso ao mapa.
- Larguras 1440, 1024, 768 e 390: sem overflow horizontal da página; modo por dia nos ecrãs pequenos; claro → escuro → claro; sem exceções JavaScript neste percurso.
- As ações de navegador foram de leitura/cancelamento; os POST de restrições são consultas do motor existente. Não foram criadas/alteradas refeições na família principal.
- A API não foi modificada neste incremento; a regressão de 441 testes passou no incremento anterior, na base isolada.
- O frontend foi reiniciado ao detetar CSS antigo em cache; a presença das regras finais no conteúdo servido foi confirmada antes da verificação final.

Capturas locais não versionadas em `.cache`: `crosscheck-prototype-home.png`, `crosscheck-prototype-week.png`, `crosscheck-app-week-before.png`, `crosscheck-app-week-v2.png`, `crosscheck-adaptation-light.png`, `crosscheck-week-390.png` e `crosscheck-week-dark.png`. As capturas da aplicação podem conter nomes da família; não publicar como fixtures públicas.

## Regra para os próximos incrementos

Por pedido do utilizador, comparar sempre o percurso alterado com o protótipo antes de o declarar pronto: referência visual, densidade, claro/escuro, comportamento em quatro larguras, detalhe progressivo e regresso com contexto. Registar as divergências que continuam abertas. O aspeto aprovado orienta a apresentação; os dados e motores demonstrativos não substituem a API real.


## Incremento seguinte — compras e despensa

Referência observada: página Compras do protótipo, título «Só falta o que faz falta», checklist, acesso «Ver despensa» e distinção explícita entre comprar e receber. A aplicação real aproxima agora essa hierarquia com cartões de resumo, checklist pesquisável e filtrável, conferência plano/despensa recolhida e ferramentas de embalagem progressivas. Avisos de cálculo permanecem visíveis por título/contagem e abrem os detalhes. A comparação de stock continua numa secção expansível, em vez da coluna lateral do protótipo; é uma divergência consciente desta fatia.

Implementado: filtros A comprar/Comprados/Recebidos/Todos; receção parcial distinta de concluída; pesquisa; acesso direto à despensa e regresso correto às receitas; embalagens carregadas só ao expandir; adição manual progressiva com validação de quantidade/unidade; aviso de período divergente sem fingir recálculo; pesquisa de stock por ingrediente/local; filtros de data próxima/ultrapassada ou em falta; lotes ordenados sem fusão e estado vazio orientado para adicionar stock. Uma data registada não é apresentada como garantia de segurança ou aptidão.

167 testes frontend e TypeScript/build passaram. O navegador foi verificado com API real em leitura e dados sintéticos intercetados para os passos de mutação da checklist. A base da família não foi alterada pelos testes. Capturas locais: `crosscheck-shopping-prototype.png`, `crosscheck-shopping-final.png`, `crosscheck-pantry-real.png`, `crosscheck-pantry-dark.png`. Teste de quatro larguras, claro/escuro/claro, pesquisa, filtros, mudança de estado e navegação. Não foi modificada a API neste lote.


## Incremento maior — da troca à refeição confirmada

O teste do utilizador mostrou que «revista» e «variante ativa» não tornavam evidente a aplicação da alteração. O protótipo mostra comparação e decisão no contexto da refeição; a app real precisava de ligar esse gesto aos estados persistidos. Novo painel no detalhe: preparar/verificar → aceitar trocas → confirmar refeição. Botões junto a cada ingrediente abrem o mesmo fluxo, e uma adaptação existente pode ser escolhida e reavaliada. O rendimento, os ingredientes concretos e as doses ficam no mesmo percurso. Resultados e dados desconhecidos continuam distintos de certificação FODMAP.

A ativação deixa a refeição original intacta. A confirmação posterior muda uma única refeição com revalidação no servidor e atualização das compras. Existe agora confirmação individual de proposta, além da semana completa; aceitar uma refeição invalida sugestões restantes em memória para recálculo. O painel ainda é inline abaixo do mapa, em vez do drawer; esta divergência visual permanece documentada. As fontes, a comparação base/alternativa e as paletas aprovadas são mantidas.

Evidência: **172 testes web, 444 testes API**, Ruff e build. E2E real em Edge headless, com API e PostgreSQL dedicados `nutriflow_ux_adaptation_e2e_20261118`, sem mocks: duas trocas, rascunho/verificação, ativação sem alterar refeição, confirmação com o mesmo evento/horário, porções de 217,5 kcal no cenário sintético e compras com massa de arroz/cebolinho em vez de trigo/cebola. Confirmação individual de uma proposta criou exatamente uma refeição. Quatro larguras, claro/escuro e ausência de exceções JS verificados. Na família principal apenas se abriu o fluxo em leitura, sem aplicar substituições ou alterar refeições.

A verificação detetou e corrigiu a perda de estado do painel quando a lista de revisões era esvaziada durante o refresh: a atualização agora preserva o conteúdo no mesmo contexto. A confirmação usa `expected_updated_at` e bloqueio de linha no servidor para recusar uma revisão desatualizada. Testes cobrem também restrição acrescentada após aceitação, sem permitir aplicar a variante entretanto incompatível. Não foi necessária migration neste lote.

Capturas sintéticas locais: `acceptance-01-verified.png`, `acceptance-02-changes-accepted.png`, `acceptance-03-meal-confirmed.png`, `acceptance-dark.png`. Instruções de utilização em [Aceitar trocas e confirmar refeição](aceitar-trocas-e-refeicao.md).


## Regressão de formatação encontrada no PDF do utilizador

A regra de largura dos inputs afetava também checkboxes, contrariando a seleção compacta do protótipo. Corrigida a especificidade e adicionada grelha explícita aos campos. O teste visual passa a verificar proporções internas, além de overflow da página: checkbox fixo e nome com largura útil nas quatro resoluções. A impressão agora tem regras próprias (sem shell, semana completa e blocos indivisíveis), evitando depender das regras mobile durante a paginação. PDF corrigido de cinco páginas renderizado/revisto; origem e saída mantêm os dados reais sem inventar rendimento ou quantidades em falta.


## Correção do fluxo pelas três imagens do utilizador

A referência de interação passou a ser explícita: figura 3 abre a comparação da figura 2; figura 1 apenas para editar manualmente. Implementado painel inicial de propostas com aceitar/ignorar/editar e acréscimo de troca para outro ingrediente. Decisões concluídas desbloqueiam «Aceitar escolhas e editar receita». A seleção de uma proposta textual com dados em falta pode avançar para completar a receita; não equivale à sua aplicação ou validação.

O formulário técnico deixa de ser a primeira vista. Não há uma segunda lista de propostas duplicada abaixo do fluxo. Voltar à lista preserva decisões e opção selecionada; o painel permanece montado, oculto durante a edição. A segunda etapa mostra só as trocas escolhidas. A terceira confirma a refeição. Ignorar tudo permite editar/continuar com a receita original, mas o servidor continua a bloquear ingredientes incompatíveis com restrições obrigatórias.

176 testes frontend e build passaram. E2E real com DB/API/frontend dedicados `nutriflow_ux_choices_e2e_20261118`: propostas primeiro, abrir/cancelar manual, aceitar/ignorar e voltar sem perder decisões, acrescentar troca manual, verificar/aceitar receita e confirmar refeição. Caso ignorar tudo avançou até confirmação mas recebeu 422 por restrições ativas, preservando a refeição adaptada. Quatro larguras, temas e ausência de exceções JS verificados. Na família principal apenas se escolheram propostas em memória e navegou-se entre etapas, sem guardar receita/variante/refeição. Capturas locais: `choices-01-proposals.png`, `choices-02-dark.png`, `choices-main-proposal.png`.


## Receita já preenchida e edição opcional

Refinamento solicitado pelo utilizador: aceitar propostas não deve obrigar a voltar a preencher a mesma troca. A segunda etapa agora é «Rever receita», com resumo das alternativas aceites e valores conhecidos. O nome escolhido é transportado explicitamente, incluindo propostas textuais sem ID, sem o substituir pelo ingrediente base. Edição completa é opcional; se faltarem identidade, quantidade, unidade, preparação, rendimento ou doses, só os respetivos campos são pedidos. Abrir edição completa preserva os valores já aceites. As porções editadas também deixam de ser reinicializadas ao voltar às escolhas no mesmo modo.

Um único «Seguir para confirmação final» guarda/verifica/ativa a variante com os serviços existentes e avança, mantendo a confirmação final da refeição separada. Receita original sem trocas usa o mesmo botão. Os dois botões intermédios anteriores foram removidos. 176 testes frontend e build passaram. E2E real em base dedicada `nutriflow_ux_review_e2e_20261118`: valores preenchidos, apenas preparação em falta pedida no cenário, edição opcional com quantidades preservadas, avanço único, gravação final real, escolhas manuais completas sem formulário obrigatório, quatro larguras/temas e recusa da receita original incompatível. Capturas sintéticas locais `review-prefilled-summary.png` e `review-prefilled-dark.png`. Verificação principal apenas em leitura/seleção local.


## Avançar com dados em falta sem fabricar uma adaptação validada

O PDF de teste mostrou rendimento ausente na receita original e alternativas apenas textuais, sem ID de catálogo/quantidade/unidade/preparação. O botão desativado escondia a diferença entre continuar a revisão e aplicar uma receita calculável. A revisão final agora é acessível mesmo nestas condições, enumera as pendências e permite guardar/retomar um rascunho persistente. Quantidades desconhecidas continuam vazias/nulas, sem copiar automaticamente o valor do ingrediente original ou inventar rendimento.

Novo armazenamento isolado `meal_adaptation_drafts`: snapshot parcial, escopo de família/receita/refeição, controlo de versão e deteção de alteração da receita base. Estes rascunhos não são receitas nem variantes ativas e não podem ser usados como recipe_id no planeador. A confirmação efetiva de trocas completas mantém todos os validadores anteriores.

Verificação de navegador real em DB/API dedicadas `nutriflow_ux_pending_e2e_20261118`: rendimento original ausente e propostas textuais, botão seguinte disponível, revisão de pendências, guardar/recarregar/retomar com vazios preservados, nenhuma variante criada e nenhuma alteração ao evento original; quatro larguras e ausência de exceções JS. Preview principal apenas verificada em leitura até à revisão; não se guardou rascunho na família real. Captura sintética local `pending-draft-review.png`.


### Campos estáveis e trocas opcionais na revisão — 18 novembro 2026

Corrigido desaparecimento durante escrita: modo de edição explícito mantém campos montados até fechar, incluindo quando todos ficam válidos. Quantidade/unidade da base usadas como ponto de partida editável; proposta explícita tem prioridade e mudança de unidade sem quantidade não converte automaticamente. Preparação conhecida exposta na API de revisão e copiada. Segunda etapa oferece acrescentar qualquer ingrediente ainda sem troca, por preferência, sem exigir restrição. Não altera o catálogo ou receita original.

Cross-check: três etapas, resumo progressivo e tokens aprovados preservados; editor completo abre quando há pendências e fecha explicitamente. 178 testes web, build/TypeScript, Ruff e 35 testes API direcionados passaram na DB isolada. Navegador real headless, API real principal em leitura: quantidade inicial 1 un, escrita de 125 e preparação sem perder campos, troca adicional na segunda etapa, quatro larguras sem overflow/erros JS; sem gravar refeições/receitas da família. Servidores locais reiniciados.


### Confirmação sem pendências artificiais — 18 novembro 2026

Preparação deixa de ser obrigatória no contrato de variantes e no frontend. Aceitar proposta sem ingrediente concreto resolve apenas correspondência exata única no catálogo; caso contrário abre imediatamente a escolha concreta, conservando quantidade/unidade. Avanço incompleto mantém revisão editável com faltas precisas, sem a antiga etapa final genérica. Rendimento existente é herdado; não se inventa rendimento ausente. Estado confirmado deriva do recipe_id de uma refeição persistida e variante ativa, nunca de aceitação local. Ocultadas propostas/formulário da base depois de aplicar; edição explícita recupera variante atual. Restrições/composição continuam verificadas pelo servidor.

180 testes frontend, build, Ruff e 36 testes API direcionados passaram em DB isolada. E2E real dedicado: proposta textual pede associação, nome exato resolve ID, preparação vazia permite criar/validar/ativar/aplicar, reload mantém estado confirmado sem propostas base e editar recupera operações; quatro larguras sem overflow ou erros JS. Base principal sem alterações a refeições/receitas.


### Regressão de aceitação direta corrigida — 19 novembro 2026

Repõe o fluxo aprovado: Aceitar proposta regista accepted imediatamente e não abre edição manual, mesmo sem ID concreto. Mantém associação automática apenas por nome exato único, valores de base e preparação opcional. Se a edição manual do mesmo ingrediente estiver aberta, aceitar/ignorar fecha-a. Identificação ainda desconhecida conserva a descrição na revisão da receita, sem inventar alimento nem modificar validação de aplicação.

181 testes frontend e build/TypeScript passaram. E2E real headless na app principal, em leitura: edição manual aberta explicitamente, aceitar fecha-a; duas propostas aceites sem formulário; passo 2 disponível; nomes/quantidades preservados; escrita de vários algarismos e navegação de volta conservadas. Nenhuma refeição/receita gravada. Servidor web reiniciado.


### Edições herdam requisitos da receita original — 19 novembro 2026

Separada edição aprovada pela família de variante nutricional validada. Novo POST recipe-variants/recipe-edit permite rendimento ausente, unidades existentes (emb), preparação ausente e descrições aceites sem ID prévio; descrições geram ingrediente privado da família sem composição fabricada. Quantidades/porções/unidades herdadas; referência de porção existente preservada sem copiar nutrientes da base. source family_adaptation e confirmation_mode recipe_edit distinguem estas edições; workflow ativo não certifica nutrição. Não há migration: usa receitas/ingredientes/FamilyRecipeVariant e evidência JSON existentes.

Aplicação verifica propriedade da família, ingredientes disponíveis, base/evidência intactas, meal type e restrições ativas conhecidas, como a base. Desconhecido nutricional fica nulo, não um valor herdado. Ativação/validação de variantes rigorosas mantém contratos existentes. Reviews incluem edições aplicadas válidas para mostrar confirmação sem repetir pendências da base. Base principal sem alterações a refeições/receitas durante testes.

Cross-check com protótipo: aceitar direto → resumo editável opcional → confirmação; nenhum campo novo obrigatório para dados ausentes na base, mais trocas opcionais mantidas. E2E real dedicado (DB nutriflow_ux_inherit_e2e_20261119): yield nulo, emb, descrições sem ID, aplicação e compras, nutrientes nulos, porções originais, reload confirmado e edição recuperada; quatro larguras sem overflow ou JS errors. 182 testes frontend/build, Ruff e 17 testes API direcionados passaram. Regressão API completa: 452 testes passaram na DB isolada. Teste direcionado adicional confirma que a edição aparece nas reviews mesmo com nutrição desconhecida. Percurso Frango de quinta-feira na app principal verificado em leitura: aceitar direto, emb/quantidades herdadas, sem editor obrigatório ou bloqueio por rendimento/ID ausente.


### Lote de 20 tarefas de navegação e autoria — 19 novembro 2026

Checklist/evidência canónicos: `docs/ux/lote-20-2026-11-19.md`, 20/20 locais. Navegação por hash com contexto de pessoa, separador, data e modo, back/forward; filtros de receitas por família/tempo/origem, ordenação, contagem e limpeza, em detalhe progressivo; cópia editável da receita com original intacto, dados opcionais preservados, pesquisa e IDs estáveis nas linhas. Guardas de alterações por guardar nas receitas/refeições, incluindo navegação e unload; identidade/quantidades preservadas em cancelar. Editor de refeição com avatares, presença em lote, pesquisa e resumo antes de guardar, mais versão esperada no update.

188 testes frontend, TypeScript/build passaram. E2E real dedicado guardou cópia e refeição sintéticas; URL/reload/back/forward, filtros, guardas, reordenação, quatro resoluções/temas/foco e ausência de JS exceptions passaram. Regressão real do percurso de adaptação também passou. Sem alterações API/migrations neste lote; a suíte API de 452 do incremento anterior não foi repetida sem alterações de backend. Dados principais não foram alterados. Protótipo HTML consultado; paletas e cinco destinos mantidos, filtros móveis recolhidos. Servidor web reiniciado para preview final.
