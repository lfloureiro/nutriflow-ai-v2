# Tarefas de implementação — planeamento familiar

Atualizado em 18 de outubro de 2026. Trabalho exclusivo no v2, branch local
`codex/health-conditions-fodmap-review`. Este quadro acompanha a execução;
o desenho detalhado está em `integrated-family-meal-planning-roadmap.md`.

| ID | Estado | Tarefa | Critério de conclusão |
| --- | --- | --- | --- |
| T01 | Concluída localmente | Completar propostas de substituição existentes | Editar e guardar quantidade/unidade/notas de preparação com validação, controlo de versão e isolamento familiar |
| T02 | Concluída localmente e verificada na interface | Variantes completas versionadas | Uma variante reúne todas as operações, produtos, quantidades, preparação e composição; mantém a base original |
| T03 | Concluída localmente para regras registadas/contexto escolhido | Validar variante para todos os presentes | Nenhuma troca parcial é apresentada como solução completa; conflitos e falta de evidência ficam visíveis |
| T04 | Parcial: presenças por refeição, cópia de semana e repetição de grupos | Presenças por refeição | Padrões, exceções, grupos, ausência/incerteza e refeições individuais funcionam na mesma semana |
| T05 | Parcial: seleção e agenda manual revalidam presentes/data | Escolher automaticamente original/variante | Entrar/sair um participante recalcula sem aplicar restrições de ausentes; escolhas fixadas são revalidadas |
| T06 | Parcial: ingrediente efetivo, produto confirmado e embalagens implementados | Comprar ingredientes efetivos | Compras da variante por porções/stock, sem ingrediente substituído nem duplicações; embalagens e quantidades confirmáveis |
| T07 | Parcial: onze produtos observados em duas lojas | Ampliar alternativas e rótulos | Priorizar ingredientes usados; produtos com fonte/data e cobertura explícita de composição, sem certificação inventada |
| T08 | Parcial: procura no detalhe da refeição | Pesquisa única e mapa | Casa/entrega/restaurante preservam participantes, data, zona e regras; mapa/lista sincronizados |
| T09 | Dependente de acesso externo | Conectores reais autorizados | Adaptadores, credenciais adequadas e testes reais; falhas isoladas por fonte; não apresentar fixtures como live |
| T10 | Por fazer | Sobras, consumo e feedback | Quantidades produzidas/consumidas/reservadas verificáveis; variedade sem relaxar regras |
| T11 | Por fazer | Fases e tolerâncias alimentares | Perfil com validade, fase e exceções individuais explícitas, distinguindo regra de planeamento de prescrição clínica |
| T12 | Consolidada e publicada na branch; revisão continua | Consolidar e preparar integração | Rever branch empilhada, migrations e testes; separar dados pessoais/backups de código; publicação autorizada pelo utilizador, com revisão e sem dados pessoais |

## Ponto de partida

Já existem percurso guiado, restrições automáticas configuradas, propostas visíveis e
onze observações de supermercado. Variantes completas já podem ser validadas e ativadas;
propostas isoladas continuam sem aplicação automática. Presenças por refeição e consultas
de semanas guardadas estão implementadas; padrões e refeições individuais permanecem pendentes.

## Registo de execução

- T01 iniciada: auditoria confirmou que POST aceita quantidade/unidade, mas PUT apenas
  permitia estado/notas. Implementar edição parcial sem apagar campos omitidos,
  validação do par quantidade/unidade, controlo de versão e teste de persistência.
- T01 implementada: PUT aceita edição do par quantidade/unidade, preserva campos omitidos
  e permite repor ambos a desconhecido. Formulário de revisão mostra quantidade da receita
  completa e unidade; notas continuam a suportar preparação. Sem alteração da receita base,
  sem quantidades inventadas e sem considerar `reviewed` como variante ativa.
- Validação T01: 21 testes da API de revisão alimentar e 99 testes frontend passaram;
  TypeScript e build de produção passaram. Não foi necessária migração da DB.
- Próxima entrega funcional: T02 + T03, começando por uma receita piloto. Resolver produto,
  composição e todas as operações da receita antes de permitir ativação/materialização.
- T02/T03: variante imutável familiar com várias trocas, cálculo nutricional completo,
  rascunho/ativação/retirada e revisões. Alterações na base/composição invalidam novo uso.
  Editor integrado no mesmo ecrã de substituições. Ver ADR-063; verificação visual em curso.
- T05/T06: testes confirmam seleção semanal da variante, bloqueio por nova restrição de
  outro participante e compras só de arroz/cebolinho em vez dos ingredientes originais.
- Regressão deste incremento: 378 testes API e 102 frontend passaram; build passou.
  A receita piloto é sintética e os testes de interface usam DB/servidores separados.
- Verificação final: 379 testes API, 104 frontend e build passaram. Percurso de interface
  concluído até guardar sete jantares e calcular as compras efetivas; regressões do resumo,
  semana já preenchida e apresentação de quantidades corrigidas. Evidência em
  `../audits/2026-10-18/complete-variant-interface-verification.md`.
- Próxima prioridade de implementação: T04, presenças por refeição, seguida da ligação
  dessas presenças à seleção original/variantes em T05. T03 não é certificação clínica;
  doses FODMAP e fases/tolerâncias continuam dependentes de evidência/perfis explícitos.

- T04: quadro de presenças por data/refeição no primeiro passo do percurso. O grupo
  habitual é o valor por omissão; exceções vazias não geram refeição. Persistência no JSON
  versionado de `FamilyWeekSetup`, sem nova migration. Validação de semana, âmbito familiar,
  refeições selecionadas, duplicados e concorrência existente.
- Motor semanal: candidatos do mesmo slot têm o mesmo grupo; slots diferentes podem ter
  grupos diferentes. Limites diários/semanais só incluem refeições frequentadas; a pesquisa
  parcial ignora pessoas ainda sem refeições. Aceitação recalcula as regras para o grupo enviado.
- T04 ainda não concluída: padrões reutilizáveis, presença incerta e refeições individuais no
  percurso guiado continuam pendentes. Uma pessoa é explicitamente assinalada e bloqueia
  avanço; continua a poder planear refeições individuais na agenda existente.
- Interface verificada: alterar uma presença não altera os outros dias; grupo de uma pessoa
  mostra aviso e bloqueia avanço; grupo vazio mostra ausência de refeição. Escolhas de teste
  repostas sem guardar alterações no plano da família. Ver `../audits/2026-10-18/meal-attendance-interface.png`.

- T05: avisos «por adaptar» na grelha filtram fontes automáticas por presentes, data e tipo
  de refeição. Não reutilizam a união de restrições da semana num jantar sem a pessoa afetada.
  Exclusões manuais continuam globais à semana. Teste integrado confirma receita base
  bloqueada com SIBO presente e aceite/materializada apenas para os dois participantes sem SIBO.

Validação final deste incremento: **383 testes API**, **106 testes frontend**, TypeScript,
build de produção, Ruff e `git diff --check` passaram. Teste SIBO/presenças cobre também
aceitação e participantes efetivamente guardados. DB principal mantém head `58960d47819f`;
nenhuma migration nova. Alterações locais, sem commit/push.

- Correção da seleção (ADR-065): retirado catálogo global do percurso. O prato selecionado
  mostra propostas próprias, incluindo caldo/farinha ainda sem referência alta; variantes
  mostram as operações completas realmente aplicadas. Editor limitado ao prato/data/presentes.
- Origens das refeições: escolha casa/entrega/restaurante guardada com a semana. Almoço
  sugere entrega; sem pratos elegíveis fica pendente, com consulta às plataformas/restaurantes
  no detalhe. Não transforma conta normal de cliente em API consumer.
- T09: utilizador confirmou conta normal apenas. Credenciais/aprovação/adaptador ausentes
  nos três fornecedores; abrir plataforma está disponível, importação automática permanece
  por ligar. Nenhuma encomenda/pagamento foi efetuado.

## Verificação final do incremento

- 114 testes frontend, TypeScript e build passaram.
- 386 testes API passaram na regressão completa; depois da extensão Nominatim, os 14
  testes focados de restaurantes/capacidades passaram na versão final. Ruff/diff check passaram.
- Interface: almoço 20/10 → pesquisar Lisboa → 12 restaurantes reais → mapa OpenStreetMap
  carregado → selecionar Tasquinha do Lagarto alterou marcador e estado selecionado da lista.
  Captura `lunch-restaurants-map.png`; não se encomendou nem se aplicou qualquer refeição.
- Mapa incorporado no detalhe, ligado à seleção da lista; sem dados clínicos na URL.
- Sem migration nova. Alterações locais, sem commit/push. Importação consumer continua
  bloqueada por ausência de contrato/acesso e adaptador reais, não apenas por falta de chave.

- ADR-066: início com semanas guardadas e trocas por prato; menu Plano abre semana.
  Agenda/dia e compras mostram alternativas na linha do ingrediente. Estados «aplicado»
  e «por aplicar» distinguem variantes materializadas de propostas. Compras mantêm as
  quantidades originais até aplicar variante válida; propostas limitadas ao intervalo guardado.

- Validação ADR-066: 118 testes frontend e build passaram; percurso real de consulta
  confirmou sete refeições guardadas com alternativas no início/agenda e compras. Sem
  alterações às refeições/quantidades guardadas. Evidência em
  `../audits/2026-10-18/saved-weeks-inline-alternatives-verification.md`.

## Consolidação e auditoria autorizadas — 18/10/2026

1. Consolidar T01–T06 e T08, testes e documentação; publicar branch v2 sem dados pessoais.
2. Auditar navegação, estados de carregamento/erro e acesso às alternativas em todos os ecrãs.
3. Inventariar tabelas, relações, índices, concorrência e coerência das migrações.
4. Ampliar T07 com produtos reais Continente/Auchan, fonte/data e nível de evidência.
5. Priorizar embalagens nas compras, presenças reutilizáveis e revalidação de escolhas fixadas.

Publicação autorizada explicitamente pelo utilizador. Backups, exportações e evidência
visual com dados pessoais ficam locais; não são incluídos no repositório público.

## Auditoria após publicação — 18/10/2026

- Consolidação publicada em `5aab9e3`; não houve merge para main.
- T07: sete novos produtos importados (total onze); farinha com tabela zerada mantém
  nutrição desconhecida, cebolinho distingue seco/fresco e laticínios conservam alerta leite.
- Interface: nível de evidência ingredientes sem nutrição; compras em chunk lazy, redução
  do JS inicial de 470,51 para 430,53 kB. Associação de catálogo por índice em memória.
- Inventário completo das tabelas em `../domain/schema-audit-2026-10-18.md`.
- Achados e prioridades em `../domain/technical-audit-2026-10-18.md`.
- Próximas tarefas: T04 padrões/individual, T05 escolhas fixadas, T06 embalagens,
  T11 fases/tolerâncias e autenticação antes de deployment público.

Validação final do incremento de auditoria: **388 testes API e 119 frontend passaram**;
TypeScript/build, Ruff completo e Alembic check passaram. Sem nova migration.

## Fases seguintes — ADR-068

- T04: copiar organização da semana anterior e repetir presenças de um tempo nos sete
  dias. Cópia mantém versão/exclusões do destino, recalcula regras e exige revisão antes
  de guardar. Semanas/pessoas indisponíveis têm mensagens explícitas.
- T05: corrigida a via manual para receitas-base: criação e alterações de participantes,
  receita ou data/tempo verificam regras ativas. Conflito rejeitado com rollback, nomes
  dos ingredientes e orientação para validar uma variante. Sem mudança de refeições reais.
- Concluído o primeiro conjunto de testes: 13 API focados e 123 frontend passaram; build passou.
- Continuam pendentes: T04 padrões nomeados/incerteza/individual no percurso; T05 seleção
  de variantes e escolhas fixadas; T06 produto confirmado/embalagens; T11 fases/tolerâncias.

- Regressão: 390 API completos e 123 frontend passaram; TypeScript/build, Ruff e Alembic
  check passaram. Caso de mais de 20 presentes acrescentado para evitar limite interno
  do compilador de restrições: validação em lotes cobre também o último participante.
- Interface: semana anterior inexistente explicada; copiar semana mantém exceções;
  repetir um grupo atualiza sete jantares. Teste apenas em estado por guardar, descartado.

Execução focada final: 14 testes de agenda/variantes passaram, incluindo grupo com
mais de 20 pessoas e rejeição do ingrediente para o último participante.

## T06 — produto confirmado e embalagens (ADR-069)

- Confirmação explícita de rótulo cria ingrediente próprio, disponível no editor de variantes;
  registo idempotente e familiar, com evidência imutável. Dados em falta não são inventados.
- Compras aceitam só o produto do ingrediente efetivo. Proposta ligada ao ingrediente
  original não permite calcular embalagens do substituto.
- Pré-visualização antes de guardar: embalagens arredondadas para cima, excedente e custo
  observado. Quantidades/estado/rótulo mudados exigem revisão; comprado mantém histórico.
- Migration 93c8e18311c4 testada com recuo e aplicada após backup; sem alterar receitas pessoais.
- 399 API completos, 20 API focados e 128 frontend passaram em verificações deste bloco;
  últimos ajustes e interface em validação. Faltam comparar lojas e entrada real de stock.

Validação final T06: 34 API focados e 128 frontend passaram; regressão completa API 399
passou neste incremento. Build, Ruff e Alembic check passaram. Interface isolada confirmou
pré-visualização → guardar 3 embalagens → recarregar → escolha preservada. Captura local
`docs/audits/2026-10-18/confirmed-shopping-packages-interface.png`, sem publicação de dados.
