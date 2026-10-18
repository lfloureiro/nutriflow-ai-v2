# Próximas alterações: planeamento familiar integrado

Incremento posterior, ADR-062: restrições pré-selecionadas por dietas estruturadas e
perfil SIBO ativo, com origem/datas visíveis e verificação por refeição no backend.
Receitas base mostram imediatamente propostas de troca. As variantes completas com
quantidades e compras substitutas continuam pendentes de implementação/validação.

Atualizado em 18 de outubro de 2026. Implementação parcial local: percurso guiado da próxima semana até às compras, escolhas persistidas, exclusões explícitas verificadas e quatro sugestões de supermercado com fontes. Ver `../domain/guided-week-planning-and-retail-alternatives.md` e ADR-061. A presença por refeição, variantes completas e descoberta integrada abaixo continuam pendentes. Este é o ponto de entrada para a sequência seguinte, prevalecendo sobre indicações antigas de próxima branch.

## Resultado pretendido

Planear cada refeição a partir de **quando, quem participa, onde e quais as restrições aplicáveis**. Nesse contexto, apresentar receitas próprias ou adaptadas, refeições para entrega e pratos de restaurantes na zona pedida, no mesmo fluxo de decisão.

Quando as regras explícitas de um participante exigem adaptação, a proposta apresenta uma variante familiar elegível para todos em vez do original incompatível. Sem essa pessoa na refeição, a adaptação deixa de ser obrigatória; o original continua sujeito às regras de todos os presentes. Registar uma doença, por si só, não permite deduzir um protocolo alimentar.

## Base verificada no v2

Branch local: `codex/health-conditions-fodmap-review`, empilhada sobre a revisão semanal. Não assumir que estas capacidades já estão em main.

- Existem Person/Family, planos/restrições com proveniência, porções individuais, ScheduleEntry e MealEvent/MealParticipant/Serving.
- Existem planeamento semanal, avaliação individual/familiar e materialização de transformações, com limitações.
- As 130 propostas para 66 receitas são sugestões em revisão, não variantes aplicáveis/certificações por porção. As 22 referências Monash são educativas; não foram importadas concentrações/limites laboratoriais.
- O histórico de condições não ativa NutritionConstraint, FoodAdverseReaction ou NutritionPlan.
- `SharedWeeklyPlanProposalCreate.person_ids` define uma lista comum para todos os slots, com mínimo de duas pessoas; os slots não têm participantes próprios. Uma semana heterogénea exige outra orquestração.
- A transformação partilhada atual gera uma operação `replace_ingredient` por variante. Receitas com vários ingredientes incompatíveis podem exigir operações combinadas.
- Plan-Fit suporta pratos externos normalizados; isso não demonstra chamadas reais de descoberta aos marketplaces.
- Na configuração local consultada existem zona de restaurantes e morada de entrega. Uber Eats, Glovo e Bolt Food estão selecionados, mas sem credenciais, enablement de consumidor ou adaptadores executáveis. Google Places não tem chave configurada; OpenStreetMap está implementado como alternativa disponível.
- O ecrã de restaurantes contém cartões/links, não um mapa interativo partilhado com o planeador. Estado de capacidade não prova uma chamada externa bem-sucedida; não foi feito teste de rede nesta revisão.

## Experiência prática para a família

### Semana habitual e exceções

Em `Refeições → Semana`, grelha segunda–domingo com pequeno-almoço, almoço, lanche e jantar. Cada célula mostra participantes por avatar/iniciais e uma ação `Quem vem?`.

Guardar padrões por pessoa, dia da semana e tipo de refeição, com validade e timezone. Atalhos: todos, dias úteis, fim de semana e copiar a semana. Rever antes de aplicar; não selecionar automaticamente toda a família por existir Family.

Estados: `participa`, `não participa`, `por confirmar`. Presença incerta não é ausência. Deixar pendente ou simular conservadoramente incluindo a pessoa, com hipótese visível. Sem participantes, a célula fica explicitamente sem planeamento.

Exceções por data prevalecem sobre o padrão: escola/trabalho, jantar fora, ausência, visita ou mudança de hora. Convidados precisam de restrições explícitas ou indicação de que não há avaliação alimentar para eles; não herdar as regras de outra pessoa.

### Grupos, local e refeição

Uma célula pode conter um grupo comum ou vários: duas pessoas em casa e outra no trabalho. Reutilizar vários MealEvents por tipo/dia, cada um com participantes próprios.

Cada grupo tem hora prevista, intenção `cozinhar / entrega / restaurante / decidir`, local/área, tempo de preparação e orçamento opcional. Morada de entrega e zona de restaurante usam defaults familiares com exceções por grupo. Não usar automaticamente a morada de casa para almoço no trabalho.

Impedir que uma pessoa fique em grupos sobrepostos sem resolver o conflito. Comer fora do grupo familiar não significa não comer: permitir escolha ou registo posterior da refeição individual, sem assumir nutrição zero.

### Decidir no mesmo painel

1. Confirmar participantes e contexto da refeição.
2. Resolver regras/protocolos ativos por pessoa, data e tipo de refeição.
3. Procurar em `Em casa`, `Entrega`, `Restaurante` ou `Todas`.
4. Apresentar opções com porções, substituições, cobertura das verificações e custo/tempo quando conhecidos.
5. Fixar escolhas e recalcular as restantes sem alterar presenças.
6. Rever e guardar; revalidar antes da materialização.

Mostrar `Receita adaptada` e `Ver alterações`: ingrediente original → alternativa, quantidades e preparação. O original continua acessível como referência, mas não como opção elegível se viola uma regra obrigatória dos presentes.

Mudar participantes reavalia a escolha e as porções. Uma refeição fixada que se torne incompatível fica sinalizada e não pode ser aplicada como válida; não apagar ou substituir silenciosamente decisões manuais.

## Lista ordenada de entregas

| Ordem | Entrega | Alterações | Critério de conclusão |
|---|---|---|---|
| 0 | Consolidar a revisão atual | Rever branch empilhada, migrations e documentação; separar código de dados pessoais/backups | Baseline identificado e CI no head revisto; sem integrar automaticamente PRs pendentes |
| 1 | Regras individuais utilizáveis | Protocolo/restrições com fonte, validade, fase quando aplicável e revisão; reutilizar NutritionConstraint/EffectiveNutritionPlan | Doença, preferência, alergia e regra alimentar distintas; regra sem evidência/avaliador não gera aprovação |
| 2 | Presenças por refeição | Padrões, exceções, grupos e participantes por slot no backend/DB/frontend | Mesma semana aceita grupos diferentes, refeições individuais, ausências e incerteza |
| 3 | Variantes familiares | Base Recipe + variante Family versionada, operações completas, quantidades e composição | Original preservado; variante reavaliada para todos; `reviewed` não equivale a `ativa` |
| 4 | Seleção automática | Resolver original/variantes pela presença e regras; serviço comum no dia/semana/edição | Entrar/sair uma pessoa muda a proposta corretamente; não regressar a original incompatível |
| 5 | Pesquisa única e mapa | Painel comum para receitas, pratos/menu e restaurantes; mapa/lista sincronizados | Alternar fonte/mapa/lista mantém pessoas, data, zona e filtros |
| 6 | Chamadas reais externas | Adaptadores autorizados, tokens, disponibilidade, timeouts, limites, falhas parciais e normalização | Só respostas reais aparecem como live; falha externa não bloqueia receitas/mapa de outra fonte |
| 7 | Aplicação e compras | Revalidação, gravação atómica, stock/reservas e lista pelos ingredientes efetivos | Não comprar ingrediente substituído; replaneamento sem duplicações; erro derivado não simula rollback da refeição |
| 8 | Consumo e aprendizagem | Porções consumidas, feedback, sintomas relatados, sobras e diversidade | Histórico preservado e aprendizagem sem enfraquecer restrições |

Etapas 1–4 constituem a primeira entrega funcional completa. Investigar acessos externos em paralelo, sem bloquear refeições caseiras; implementar experiência unificada/mapa e conectores nas etapas 5–6.

### Regras e evidência

Confirmar explicitamente o que excluir/limitar/testar e respetivo período. Em FODMAP, fase e tolerâncias são fornecidas, não deduzidas de SIBO.

Separar medições por produto/preparação/dose de categorias educativas gerais. Priorizar alho/cebola e preparados, leite/natas, massas/espessantes, leguminosas/cogumelos e misturas realmente usadas. Resolver rótulos, unidades e rendimento em falta antes de calcular porções.

Integrar a avaliação de tolerância/restrições em MealPlanFit, reutilizado por todas as fontes. `unknown` relevante para regra obrigatória não permite certificar compatibilidade. Orientações qualitativas não avaliáveis mantêm a cobertura explícita, sem aprovação inventada.

### Modelo de presença proposto

Conceitos lógicos, ainda sujeitos ao desenho final de migração:

- `FamilyMealAttendancePattern`: pessoa, dia da semana, tipo de refeição, estado, grupo/local, validade.
- `FamilyMealAttendanceOverride`: pessoa, data local, tipo/hora, grupo/exceção, revisão.
- `PlanningMealGroup`: slot/grupo estável, participantes resolvidos, incerteza, instante e contexto de fonte/local.

ScheduleEntry continua a descrever agenda/indisponibilidade; não duplicar trabalho/escola. MealParticipant representa a participação materializada, não o padrão recorrente.

O servidor resolve/valida `person_ids` por grupo/slot e usa o planeador individual para uma pessoa e o partilhado para várias. Não repetir a lista global em 28 slots. Projetar todas as escolhas de cada pessoa antes de validar limites diários/semanais, incluindo refeições individuais e grupos distintos no mesmo dia.

Caches/propostas dependem de participantes, revisões de presença/regras, data/timezone, contexto e versões de variante/composição. Mudanças invalidam propostas antigas; a aceitação revalida tudo no servidor.

### De proposta a variante utilizável

Reutilizar Recipe, snapshots e MealTransformationApplication; estender operações ordenadas em vez de criar outro motor.

Uma variante contém base/composição de origem, conjunto completo de operações, pesos/unidades, preparação, regras pretendidas, fonte e estado `rascunho / revista / ativa / retirada`. Ativar exige verificações suportadas; não basta marcar a proposta atual como revista. Mudança da receita base exige revalidação da variante.

Receitas globais mantêm-se imutáveis; a variante pertence à Family. Não criar uma cópia permanente por pessoa/refeição. Preparação comum deve servir todos; preparações separadas precisam de ingredientes/operações efetivamente separados. Retirar alho do prato depois de cozinhar a base comum não equivale a não o usar.

| Situação | Comportamento |
|---|---|
| Nenhum presente exige adaptação | Original e variantes elegíveis podem ser ordenados pelos critérios normais |
| Regra obrigatória de um presente incompatível com original | Apresentar variante validada para todos como principal e explicar trocas |
| Pessoa com essa regra ausente | Não impor a regra do ausente; avaliar as dos presentes |
| Variante resolve uma regra mas viola outra pessoa | Rejeitar variante e procurar outra ou preparações separadas |
| Troca isolada deixa outros ingredientes incompatíveis | Avaliar combinação completa; não chamar solução ao resultado parcial |
| Falta produto/preparação/dose/evidência obrigatória | Pendente/não verificável, sem fallback incompatível |
| Só há doença registada, sem regras explícitas | Mostrar protocolo em falta; não deduzir dieta |
| Presença por confirmar | Explicitar hipótese conservadora ou deixar pendente |

## Integração de entregas, restaurantes e mapa

### Diagnóstico por fornecedor

| Fonte | Já existe | Ação seguinte |
|---|---|---|
| Receitas | Catálogo, bootstrap, recomendações e MealPlanFit | Variantes completas e participantes por slot |
| OpenStreetMap | Nominatim/Overpass, coordenadas, cache e atribuição | Teste com área pedida, delimitação geográfica clara, mapa integrado e gestão de falhas/quotas |
| Google Places | Text Search New, FieldMask, paginação e fallback OSM | Chave/configuração/billing, teste real, centro/raio e mapa/atribuição/retenção compatíveis com o fornecedor |
| Uber Eats | Interface de adaptador, registry, sync/normalização e testes | Aprovação Consumer Delivery, especificação/credenciais adequadas e adaptador executável/testes de contrato |
| Glovo | Capacidade e pipeline genérico de sync | Confirmar contrato autorizado de descoberta de consumidor; implementar apenas contrato concedido |
| Bolt Food | Capacidade e registry | Confirmar acesso de consumidor e adaptador; não equiparar integração POS a marketplace |

[Uber Consumer Delivery](https://developer.uber.com/docs/consumer-delivery/introduction) descreve descoberta/menus para consumidores, mas acesso early-access e aprovação caso a caso. A [Glovo Partner API](https://qcommerce.developer.glovoapp.com/en/documentation/api-partner-api-overview) descreve operações para parceiros; não comprova pesquisa geral de marketplace pelo consumidor. O código de mapas já usa [Google Text Search New](https://developers.google.com/maps/documentation/places/web-service/text-search). Fontes verificadas em 18/10/2026; rever contratos na implementação.

Não basta adicionar uma chave. Distinguir sem credenciais, acesso pendente, adaptador ausente, indisponível e ativo com resposta observada. Não chamar live a fixtures nem confundir configuração com conectividade ou evidência alimentar.

### Pesquisa comum

Um serviço recebe grupo/data/hora/local/fontes, resolve regras localmente e chama conectores adequados. Normalizar resultados reutilizando FoodItem/Recipe, composições, MealCandidateAvailability, MealCommercialOffer e identidades de fornecedor.

No mesmo painel distinguir:

- **Refeições avaliadas:** prato concreto, porção e regras verificadas, com cobertura explícita.
- **Pratos por confirmar:** item real, mas falta evidência necessária; não recebe o mesmo selo de compatibilidade.
- **Locais descobertos:** restaurante no mapa ainda sem prato avaliado; cozinha, estrelas ou etiqueta vegetariana não provam adequação.

Guardar pedidos de adaptação e respetivas confirmações. Escrever “sem cebola” numa observação não prova que caldo/molho sejam adequados. Alergénios/contaminação cruzada, quando relevantes, exigem informação própria.

Preservar identidade de prato/fornecedor, fonte/instante, preço/moeda/taxas, disponibilidade e customizações. Mínimos de encomenda são contexto do conjunto; não comparar numericamente moedas diferentes.

Não enviar diagnósticos/histórico clínico aos serviços. Enviar apenas contexto comercial necessário e pedidos alimentares explicitamente autorizados. Compra/pagamento são uma ação posterior explícita; esta sequência trata descoberta e planeamento.

### Mapa no contexto da refeição

Mapa/lista partilham zona e filtros. Marcador representa local; selecionar abre pratos ou ação de obter/confirmar menu. Permitir área escrita, centro+raio e uso explícito de localização; mostrar área efetiva. Mudar zona atualiza descoberta sem apagar participantes/regras.

Rever a deduplicação atual por nome/domínio, que pode colapsar filiais diferentes. Rever também a prioridade automática por tipo que pode favorecer fast food; restrições/nutrição pertencem ao prato, com qualidade/distância/preço como critérios claros posteriores.

Falhas são independentes por fornecedor; repetir só a fonte afetada e conservar resultados válidos. Cache deve respeitar morada/zona/hora/filtros relevantes. Revalidar disponibilidade/menus antes da escolha final. Respeitar políticas de atribuição, retenção e utilização dos fornecedores escolhidos.

## Outras integrações já pretendidas nos documentos

| Capacidade | Estado e próximo passo | Referência |
|---|---|---|
| Agenda trabalho/escola/treino | ScheduleEntry existe; ligar a presença/local/tempo disponível | `docs/domain/schedule-model.md` |
| Despensa e compras | Lotes/listas existem; compra realizada → reconciliação de stock e reservas | `docs/domain/pantry-shopping-workflow.md` |
| Sobras e preparação antecipada | Faltam produção, conservação, reserva e consumo com evidência | `docs/development-continuity.md` |
| Planos profissionais/documentos | Import/revisão/texto existem; OCR de fotos/scans e mais orientação avaliável pendentes | `docs/vision/nutrition-plan-guidance-roadmap.md` |
| Catálogo confiável | Enriquecimento existe; melhorar correspondências, pesos, compostos e dados FODMAP autorizados | `docs/domain/nutrition-enrichment.md` |
| Feedback/diversidade | Eventos/preferências existem; melhorar variedade entre semanas/proteínas | `docs/domain/smart-meal-recommendation.md` |
| Saúde/atividade | Fundações para Apple HealthKit, Android Health Connect, Garmin, Withings, Oura e Fitbit; distinguir de sincronização real | `docs/architecture/target-architecture.md`, `docs/vision/product-vision.md` |
| Sintomas/tolerâncias/consumo | Ligar relatos temporais a porções consumidas, sem inferir causalidade ou mudar protocolos automaticamente | `docs/domain/health-conditions-and-fodmap-review.md` |
| Privacidade/acesso | Autenticação, autorização por pessoa, partilha consentida e segredos/vault antes de exposição pública | `docs/architecture/provider-secrets-and-vault.md` |
| Mobile/idiomas/acessibilidade | PT/EN e responsividade existem; integrações nativas e sincronização continuam posteriores | `docs/architecture/target-architecture.md` |

## Casos mínimos de aceitação

1. Jantar a quatro com uma exclusão explícita de alho/cebola: variante completa elegível apresentada em vez do original incompatível.
2. Pessoa ausente no dia seguinte: permitir original se cumprir regras dos presentes.
3. Adicionar participante a refeição fixada incompatível impede aplicação sem revisão.
4. Almoço individual e jantar partilhado coexistem e projetam nutrição correta por pessoa.
5. Grupos distintos no mesmo horário usam participantes/locais/ofertas próprios, sem duplicar pessoas.
6. Variante não resolve regra de uma pessoa violando alergia/regra de outra.
7. Mudança de presença, regra, receita ou rótulo entre preview/aplicação força revalidação.
8. Compras usam ingredientes da variante e porções/stock reais, sem conservar os substituídos.
9. Casa/entrega/restaurante na mesma pesquisa; prato sem evidência obrigatória fica por confirmar.
10. Mudar área atualiza mapa/lista sem perder participantes; filiais diferentes não desaparecem por domínio comum.
11. Fornecedor externo indisponível não bloqueia receitas/outras fontes; fixtures não aparecem como live.
12. Histórico consumido preserva composição/variante/regras utilizadas.

## Próximo incremento concreto

Começar por **presenças por refeição + regras utilizáveis + uma receita piloto com variante completa**, demonstrando a entrada/saída da pessoa com restrição no planeamento diário e semanal. Escolher receita com ingredientes/porções verificáveis, depois generalizar ao catálogo. Em paralelo resolver acessos externos; seguir com pesquisa integrada/mapa e adaptadores reais autorizados.

Não criar novos menus operacionais isolados de fornecedor. Os ecrãs existentes podem permanecer como ferramentas secundárias; a ação normal de escolher o que comer parte da refeição.
