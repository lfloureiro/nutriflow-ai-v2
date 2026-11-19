> **Estado atual — 19 novembro 2026:** consultar [passagem e próximos passos](../handoff-2026-11-19.md) e o [quadro UX](../vision/ux-revamp-task-board.md). Os estados de branches, contagens e “próxima tarefa” abaixo são históricos. Esta entrega consolida o revamp, o fluxo de trocas e o lote de 20; NLP/ML treinado e restantes fases continuam na sequência canónica.

# Transformação do UX do NutriFlow AI

Backlog preparado em 18 novembro 2026, após [auditoria local e GitHub](../ux/auditoria-ux-2026-11-18.md). Referência visual: protótipo aprovado **NutriFlow AI / Casa à Mesa**, claro marfim/verde e escuro carvão/âmbar.

Este é um plano de execução, não uma lista de funcionalidades já implementadas. O estado de execução está no registo abaixo; quando a capacidade já existe na branch, a tarefa é integrá-la no novo UX e verificar a sua preservação. Nenhuma tarefa autoriza eliminar funcionalidades para obter uma interface mais simples.

## Primeiro incremento local em execução

18 novembro 2026 · branch `codex/ux-foundation-preview`, baseada em `e34d9e0` da branch avançada. O utilizador autorizou iniciar a transformação e disponibilizar preview local; os PRs anteriores continuam sem merge. Esta é uma branch empilhada de preview, não uma declaração de consolidação de main.

| Tarefas | Estado real deste incremento |
|---|---|
| UX-001 | Baseline identificado e alterações isoladas; consolidação/merges continuam pendentes |
| UX-003 | PostgreSQL principal acessível e head confirmado; criada DB separada `nutriflow_ux_validation_20261118`; migrations e Alembic check passaram; 438 testes API passaram; backup/restauro não executado neste lote |
| UX-005–006 | Tokens semânticos e aliases, paletas aprovadas, marca e ícones implementados localmente; revisão visual nas quatro resoluções ainda pendente |
| UX-007 | Primeiras primitivas Panel/EmptyState e componentes de identidade; restantes controlos comuns por migrar |
| UX-008 | Shell visual e acessos ajustados; URLs/contexto/roteamento ainda pendentes |
| UX-009–010 | Avatares com criança/adolescente/adulto jovem/adulto/meia-idade/sénior, cabelo completo, seis variantes e apresentação configurável. Escolhas persistidas por pessoa via API, independentes de dados demográficos; home/lista/perfil consistentes e pele comum por família. Presença/porções por integrar |
| UX-011 | Scroll sem barras, foco e movimento reduzido implementados; revisão de acessibilidade completa pendente |
| UX-012 | Nova home com dados da API, quatro slots, próxima refeição, família e semanas guardadas em detalhe; detalhe de saúde preservado no perfil; abrir refeição individual ainda passa pela agenda |
| UX-013 | Entrada com nome primeiro; localização e fontes em detalhe progressivo; marca alinhada. Autenticação/remoção de ID técnico pendentes |
| UX-014 | Criação com perfil energético opcional e data de nascimento opcional; crianças sem cálculo adulto; formulário fecha após sucesso; edição e validação visual completa ainda pendentes |
| UX-018 | Catálogo em cartões, dados/evidências preservados; navegação com Receitas/Ingredientes/Despensa e ferramentas secundárias; avaliações individuais já acessíveis no detalhe da receita (incluindo partilhadas), carregadas ao expandir; gosto continua separado de segurança |
| UX-023–025, 034 | Fluxo corrigido pelas imagens do utilizador: propostas primeiro (aceitar/ignorar/manual) → aceitar escolhas e editar receita → verificar/aceitar receita → confirmar refeição. Várias trocas completas, catálogo/quantidade/preparação/rendimento/doses, variante existente, confirmação de refeição guardada ou proposta e recálculo de compras. API revalida e recusa snapshot desatualizado. Detalhe ainda inline; evidência FODMAP/dose e restantes percursos continuam por completar |
| UX-027, 031 | Semana com quatro linhas alinhadas, resumo de guardado/proposta/vazio, modo mobile por dia e editor manual por espaço vazio; cancelamento preserva dia/tempo; detalhe abaixo do mapa, drawer ainda pendente |
| UX-037–041 | Compras com resumo e checklist pesquisável/filtrável, conferência de stock recolhida, embalagens progressivas e navegação direta à despensa. Stock com pesquisa, ordenação por data e filtros; lotes separados. Estados comprado/parcial/recebido preservados. Não completa reservas, planeamento de consumo nem equivalência de rótulos |
| UX-063 | 177 testes web passaram; TypeScript/build e Ruff passaram. 447 testes API passaram na DB isolada, incluindo persistência/reset/validação de aparência sem alterar dados demográficos; migrations e Alembic check passaram. Verificação headless Edge: escolhas dos quatro avatares, consistência no perfil, seletor de seis estilos, claro/escuro e ausência de overflow horizontal em 1440/1024/768/390; sem exceções JavaScript neste percurso. Painel contextual de avaliações das quatro pessoas também verificado em leitura. Não equivale à auditoria E2E completa |

[Cross-check com o protótipo](../ux/crosscheck-prototipo-2026-11-18.md) registado; comparação passa a acompanhar cada incremento.

Correção adicional: botão Definições com engrenagem e texto explícito; clicar novamente mantém o ecrã. Refresh atualiza os dados sem forçar regresso à home. API reiniciada e campos novos confirmados por HTTP; nenhuma escrita na família principal.

Preview local: interface `http://127.0.0.1:5173`, API `http://127.0.0.1:8000`. A API da preview usa a configuração local existente; as verificações destrutivas das fixtures foram executadas exclusivamente na DB de validação. No primeiro incremento não houve seeds/migrations/escritas na base principal. No terceiro, após backup `backups/ux-before-avatar-20261118.dump`, aplicou-se a migration aditiva `c2a91f4e780d` (JSON nullable em persons) e guardaram-se as quatro escolhas de avatar pedidas pelo utilizador via PATCH; datas de nascimento e cálculos preservados. Não houve seeds nem alterações a refeições.

## Como executar

- **P0**: condição de integridade do baseline ou de disponibilização pública. Autenticação P0 não impede desenhar/testar localmente com dados sintéticos.
- **P1**: percurso central e identidade visual; iniciar assim que as dependências necessárias estejam resolvidas.
- **P2**: completar produto e roadmap por incrementos, mantendo a mesma linguagem visual.
- **EXT**: depende de acesso, dados ou contratos externos. Desenvolver contratos, UX e estados de indisponibilidade sem simular integração real.
- Dependências indicadas por ID; cada tarefa inclui as validações apropriadas. As tarefas de QA final não substituem testes em cada incremento.
- ADR-007: branch focada, documentação, testes, gates, PR/CI no head exato e integração controlada. Resolver primeiro os PRs empilhados; não começar uma nova feature sobre um `main` local antigo.

Não há estimativas de calendário nesta versão: a dimensão real depende da consolidação da branch, do acesso aos dados e da validação do primeiro percurso. Cada linha deve originar uma entrega pequena e verificável; dividir novamente antes de implementar se necessário.

## Fase 0 — Baseline e evidência

| ID | Prioridade / dependências | Tarefa e base a reutilizar | Conclusão observável |
|---|---|---|---|
| UX-001 | P0 · nenhuma | Consolidar estado Git e estratégia dos PRs #70–#74; comparar local/main/remote, proteger alterações locais e dados | Baseline e ancestralidade documentados; integração sem commits duplicados; CI do head escolhido verde; sem merge automático por estarem cinco PRs abertos |
| UX-002 | P1 · 001 | Normalizar o estado dos roadmaps, T01–T12, continuidade e implementation-status | Uma capacidade tem um estado canónico e SHA; entradas históricas não contradizem o “próximo trabalho”; features locais não aparecem como integradas em main |
| UX-003 | P0 · 001 | Disponibilizar ambiente e família sintética isolados para API, migrations e UX | Regressão API e migration check executáveis sem tocar na família real; backup/restauro verificados; seeds explícitos e idempotentes |
| UX-004 | P1 · 003 | Registar baseline E2E/visual e contratos dos principais percursos antes da alteração | Capturas sintéticas dos ecrãs atuais, quatro viewports, inventário de rotas e falhas; separar observações reais de riscos de código |

## Fase 1 — Sistema visual, movimento e primeira entrega visível

| ID | Prioridade / dependências | Tarefa e base a reutilizar | Conclusão observável |
|---|---|---|---|
| UX-005 | P1 · 001 | Substituir tokens e cascata visual pelos temas aprovados; mapear tokens antigos para semânticos | Claro marfim/verde e escuro carvão/âmbar em superfícies, campos e painéis; claro→escuro→claro/Sistema com fundo computado correto e preferência persistente |
| UX-006 | P1 · 005 | Marca, tipografia, ícones SVG, espaçamento e imagens locais/otimizadas | NutriFlow AI em relevo, Casa à Mesa subtítulo; ícones consistentes; textos longos/PT/EN sem cortes; fontes com fallback e imagens com origem/alt adequados |
| UX-007 | P1 · 005–006 | Criar componentes comuns: botão, campo, tabs, estado, lista, cartão, painel/dialog, skeleton e toast | Uma biblioteca pequena reutilizada em duas superfícies reais, com foco, validação, carregamento/erro/vazio; sem novo conjunto de overrides por ecrã |
| UX-008 | P1 · 007 | Novo shell e rotas/contexto: Início, Plano, Receitas, Família, Compras; Despensa e definições como acessos coerentes | URL/voltar/recarregar abrem a mesma semana/pessoa/receita; cinco entradas no mobile; todas as funções de Casa têm destino mapeado; rascunhos não se perdem silenciosamente |
| UX-009 | P1 · 006–007 | `PersonAvatar` com iniciais/ilustração e estados de presença/seleção | Mesma pessoa tem identidade consistente em família, semana, porções e feedback; seleção e presença confirmável pelo teclado; alternativa estática; sem informação clínica implícita |
| UX-010 | P1 · 007–009 | Movimento contextual: avatares, painéis, alteração de porções e atualização de célula | Transições de 120–220 ms conforme especificação; destaque único da refeição certa; sem loops distrativos; `prefers-reduced-motion` remove deslocação/escala sem perder estados |
| UX-011 | P1 · 007–010 | Acessibilidade e preferências globais, scroll sem barras intrusivas, PT/EN e unidades | Scroll funciona por toque/rato/teclado; nada fica cortado; foco e contraste verificados; zoom 200%; datas/fusos e unidades coerentes; sem frames de captura persistentes após QA |
| UX-012 | P1 · 008–011 | Portar a home: próxima refeição, decisões pendentes, família e atalhos práticos | A home já mostra a nova identidade com dados reais da API; abre a refeição/semana certa; métricas de saúde ficam em detalhe, preservando acesso |

## Fase 2 — Família e necessidades individuais

| ID | Prioridade / dependências | Tarefa e base a reutilizar | Conclusão observável |
|---|---|---|---|
| UX-013 | P1 · 007–008 | Simplificar criação da família e entrada; reutilizar Family API | Nome e contexto essencial primeiro, fornecedores depois; ID técnico apenas em ferramentas de desenvolvimento; estado vazio conduz a adicionar pessoas |
| UX-014 | P1 · 013 | Reformular criação/edição de pessoas com perfil energético opcional | Pessoa/criança pode ser criada sem peso/altura; cálculo adulto continua disponível quando aplicável; metas, medições e atividade editáveis sem bloquear o início |
| UX-015 | P1 · 014 | Painel de alergias, intolerâncias, exclusões, preferências, fases e tolerâncias | Fonte, severidade, validade, confirmação e incerteza visíveis; política SIBO/FODMAP explicitamente configurada, sem inferir protocolo só do diagnóstico; integração em MealPlanFit |
| UX-016 | P1 · 014–015 | Perfil nutricional: plano profissional, objetivos, regras, frequências e histórico | Um resumo legível leva a fonte/revisão/versões; regra ativa imutável; confirmar importação e ativar plano são ações distintas; perfis distintos não partilham regras por engano |
| UX-017 | P1 · 008, 013 | Definições e administração: família, contas, idiomas, fornecedores e consentimentos | Separação User/Person/Family clara; configurações secundárias não dominam onboarding; permissões reais dependem de UX-060 e não são simuladas como proteção |

## Fase 3 — Receitas, ingredientes, avaliação e variantes

| ID | Prioridade / dependências | Tarefa e base a reutilizar | Conclusão observável |
|---|---|---|---|
| UX-018 | P1 · 007–008 | Catálogo de receitas e avaliações individuais; reutilizar RecipePreferences | Pesquisa/filtros compactos; estrelas por pessoa, limpar e média das respostas; acesso na receita e após refeição; gosto separado de adequação e score do motor |
| UX-019 | P1 · 018 | Editor de receita: rendimento, preparação, ingredientes ordenados, quantidade/unidade e fonte | Adicionar/reordenar/remover linhas preserva campos; edição/desativação segura; nutrição calculada pelo servidor; original/histórico preservados; unidades ambíguas não são inventadas |
| UX-020 | P1 · 019 | Catálogo e enriquecimento de ingredientes/produtos | Procurar/criar/editar/desativar, fonte e versão de composição; ingredientes compostos e rótulos distinguíveis; desconhecido não vira zero; recálculo mantém snapshots históricos |
| UX-021 | P1 · 019–020, 049 | Importar receitas por texto e URL com revisão NLP | Pipeline com extração estruturada, rendimento/preparação/ingredientes e falhas explícitas; URL real consultado só pela integração suportada; revisão/correção antes de guardar; origem preservada |
| UX-022 | P2 · 020–021, 053 | Correspondência semântica ingrediente–catálogo e receitas semelhantes | Embeddings devolvem candidatos com proveniência; utilizador revê correspondências ambíguas; nenhum equivalente nutricional inferido só pela semelhança do nome |
| UX-023 | P1 · 015, 019–020 | Portar autoria de variantes completas; reutilizar RecipeVariant e editor existentes | Várias operações, produtos, quantidades e preparação no mesmo painel; validar/ativar/retirar; base alterada invalida utilização até revalidação; original global não é editado |
| UX-024 | P1 · 009–010, 023 | Painel de adaptação no contexto da refeição | Problema e participante → antes/depois → editar/aceitar/descartar; atualização da célula selecionada; distingue proposta/revista/ativa/aplicada; sem aplicar troca parcial como solução completa |
| UX-025 | P1 · 015–016, 024 | Avaliação de refeição por pessoa: nutrição, restrições, FODMAP e cobertura | Mostra contribuição da porção e contexto diário/semanal; conflito obrigatório domina score; desconhecido permanece pendente; nenhuma aprovação clínica por categoria educativa ou estrelas |
| UX-026 | P1 · 019, 023–025 | Histórico e proveniência de receita, variante, porção, regra e cálculo | Alterar catálogo/receita não reescreve o consumido; utilizador consegue perceber qual versão foi aplicada e o que requer nova revisão |

## Fase 4 — Semana, presença e decisão no mesmo percurso

| ID | Prioridade / dependências | Tarefa e base a reutilizar | Conclusão observável |
|---|---|---|---|
| UX-027 | P1 · 008–012 | Reconstruir apresentação Hoje/Semana com a nova estrutura; reutilizar FamilyMeals/WeeklyProposal | Sete dias e quatro tempos, vazios visíveis; desktop legível e mobile por dia; abrir/voltar preserva seleção; refeições guardadas e propostas visualmente distintas |
| UX-028 | P1 · 009, 014, 027 | Completar presenças reutilizáveis: padrões, datas, exceções e incerteza | Copiar/repetir existentes preservados; padrões nomeados com validade/fuso; “por confirmar” não é ausência; visitantes têm dados/restrições próprios ou cobertura explicitamente em falta |
| UX-029 | P1 · 028 | Integrar refeições individuais e vários grupos/locais por slot | Uma pessoa e família usam o mesmo percurso; casa/trabalho/escola/restaurante coexistem sem duplicar participantes; refeições fora do grupo continuam a contar no dia da pessoa |
| UX-030 | P1 · 024–029 | Fixar escolhas e revalidar após alteração de presença, regras ou receita | Escolha fixada permanece visível; contexto incompatível impede aplicação sem revisão; recalcular o resto não troca escolhas manuais nem ignora novo participante |
| UX-031 | P1 · 019, 025–029 | Editor manual completo: adicionar, substituir, copiar, repetir, cancelar e estados de consumo | Data/hora/local/receita/participantes/porções editáveis; cancelamento preserva histórico; preparado/servido/concluído protegidos conforme domínio; retries idempotentes |
| UX-032 | P1 · 015–016, 027–029 | Critérios contextuais numa interface curta | Tempo, agenda/cozinha, orçamento quando conhecido, fontes, preferências e variedade; sem união permanente de restrições de pessoas ausentes; transparência sobre campos sem evidência |
| UX-033 | P1 · 025, 029–032 | Portar geração semanal e otimização existente para o novo fluxo | Etapas reais de carregamento; opções elegíveis por pessoa; limites combinados do dia/semana; ausência de solução explicada; proposta não materializa refeições antes da aceitação |
| UX-034 | P1 · 030–033 | Aceitação, concorrência, descarte e respostas desatualizadas | Mudança de família/semana/pessoa invalida pedido antigo; aceitar revalida no servidor; guardar é atómico; compras com erro posterior não simula rollback de refeições já guardadas |
| UX-035 | P1 · 025, 029, 033 | Porções e contexto energético/nutricional do dia | Planeado/servido/consumido distintos; unidade e derivação seguras; alvos diários não tratados como por refeição; equilíbrio familiar não compensa falha obrigatória individual |
| UX-036 | P2 · 033, 042, 051 | Variedade entre semanas, rotação e preparação antecipada | Respeita critérios de grupos/proteínas com dados estruturados; repetição é preferência suave quando apropriado; não inventa sobras; preferências aprendidas só entram após UX-052 |

## Fase 5 — Despensa, compras e ciclo de utilização

| ID | Prioridade / dependências | Tarefa e base a reutilizar | Conclusão observável |
|---|---|---|---|
| UX-037 | P1 · 007–008, 020 | Portar despensa: lotes, quantidade, unidade, local, validade e retirada/reativação | Lista simples; detalhe progressivo; stock observado distinto de previsão; validade avaliada para a hora das refeições e distribuição FEFO preservada |
| UX-038 | P1 · 024, 034–037 | Nova lista de compras pelo plano e ingredientes efetivos | Necessário/em stock/previsto/falta claros; variante aplicada elimina compras do ingrediente substituído; refresh explícito; itens manuais e comprado mantidos; sem duplicar faltas |
| UX-039 | P1 · 020, 038 | Painel de rótulo, produto confirmado e evidência | Confirmar ingrediente real requer fonte/rótulo atual; composição desconhecida visível; rótulo alterado exige revisão; alternativa comercial não é equivalência clínica |
| UX-040 | P1 · 039 | Embalagens, excedente e comparação contextual de lojas | Reutiliza preço por embalagem/kg/l e snapshots; compra é do ingrediente efetivo; moedas/unidades não comparáveis bloqueiam números enganosos; preço observado tem data/fonte |
| UX-041 | P1 · 037–040 | Portar comprado/recebido, entregas parciais, vários lotes e fecho incompleto | Quantidade prevista não conta como disponível; retries não duplicam stock; fecho recalcula falta; histórico e concorrência preservados; ETA futura só quando fornecida |
| UX-042 | P2 · 026, 031, 035, 037–041 | Consumo real, produção, sobras, reservas e correções/estornos | Registar o produzido, consumido e reservado com conservação/validade; correção auditável sem apagar histórico; plano seguinte usa apenas sobras efetivamente disponíveis |
| UX-043 | P2 · 040–042 | Custo do cesto por loja/entrega e atualização de catálogo | Distingue orçamento, soma observada e total realmente confirmado; custos/entrega/mínimos/fontes atualizados; cobertura de rótulos aumenta sem inventar live ou dados nutricionais |

## Fase 6 — Fontes externas no contexto da refeição

| ID | Prioridade / dependências | Tarefa e base a reutilizar | Conclusão observável |
|---|---|---|---|
| UX-044 | P2 · 024–025, 029, 032 | Pesquisa única Em casa / Entrega / Restaurante / Todas | Pessoas, data/hora, área e restrições mantêm-se ao alternar fontes; distinção entre restaurante, prato por confirmar e prato avaliado; nenhum menu principal isolado por fornecedor |
| UX-045 | P2 · 044 | Estados de capacidade e configuração contextual de fontes | Sem acesso, sem configuração, sem adaptador, indisponível e resposta observada são distintos; links de conta normal disponíveis sem prometer importação consumer |
| UX-046 | P2 / EXT · 044–045 | Evoluir mapa/lista OSM e Google, deduplicação e zona/raio | Lista e marcadores sincronizados; filiais não colapsam só pelo domínio; área efetiva visível; zona muda sem perder refeição; atribuição/cache/contratos verificados na implementação |
| UX-047 | EXT · 045, 060–061 | Adaptadores reais autorizados Uber Eats/Glovo/Bolt Food | Confirmar contratos de descoberta consumidor e acessos; implementar só o permitido; testes de contrato e respostas reais; fixtures e credenciais POS não aparecem como marketplace live |
| UX-048 | P2 · 025, 044–047 | Normalização, revalidação e falhas independentes por fornecedor | Preço/disponibilidade/prato com fonte/instante; falha de uma fonte não apaga outras; consentimentos e pedidos alimentares mínimos; sem diagnósticos nas URLs/chamadas; pagamento continua ação própria |

## Fase 7 — NLP, ML, deep learning e confiança

| ID | Prioridade / dependências | Tarefa e base a reutilizar | Conclusão observável |
|---|---|---|---|
| UX-049 | P1 · 016, 007 | Portar importação de plano: ficheiros/texto/API IA/assistência ChatGPT | Caminhos existentes preservados; extração e interpretação distintas; fonte original e ambiguidades; edição, confirmação e ativação separadas; erro de configuração não perde texto/revisão |
| UX-050 | P2 · 049 | OCR de fotos/scans e acessibilidade documental | Texto extraído revisto antes de interpretar regras; qualidade/confiança e páginas problemáticas visíveis; ficheiros não legíveis não geram regras inventadas |
| UX-051 | P1 · 018, 026, 031 | Eventos e conjuntos de dados para aprendizagem | Decisões aceitar/recusar/editar, gostos e consumo com contexto temporal; consentimento/anonimização; referências sintéticas distintas; divisão treino/validação/teste sem leakage |
| UX-052 | P1 · 025, 051 | Recomendador ML treinado, baseline e avaliação por pessoa/família | Comparar com heurísticas atuais e popularidade; métricas em teste separado; cold start e fairness medidos; modelo ordena só candidatos elegíveis; não chamar pesos fixos “modelo treinado” |
| UX-053 | P1 · 020–021, 051 | Embeddings/deep learning e avaliação NLP | Conjunto anotado de extração/correspondência; comparar lexical e semântico; reportar precisão/recall/F1 e Recall@k/MRR conforme tarefa; modelo/versão/licença documentados; sem métricas inventadas |
| UX-054 | P2 · 052–053, 061 | Ciclo de modelos e operação de IA | Artefactos versionados, avaliação antes de promover, rollback, monitorização de deriva/latência/custo; falha do modelo mantém percurso manual e baseline seguro |
| UX-055 | P1 · 024–025, 033, 049, 052 | Explicações no produto e avaliação humana | “Porque esta sugestão?”, fontes e cobertura compreensíveis; distinção entre inferência, cálculo, regra e preferência; feedback de clareza medido; sem scores como selo clínico |

## Fase 8 — Saúde, mobile, privacidade e operação

| ID | Prioridade / dependências | Tarefa e base a reutilizar | Conclusão observável |
|---|---|---|---|
| UX-056 | P2 · 014–017, 025–026 | Saúde, atividade, agenda e histórico em detalhe progressivo | Fundações existentes acessíveis sem ocupar a home; medições e relatos com origem/tempo; sintomas/tolerâncias ligados a consumo sem inferir causalidade ou diagnóstico |
| UX-057 | P2 / EXT · 056, 060–061 | Health Data Hub e primeiros conectores reais | Consentimento por pessoa/dado, proveniência e deduplicação; Apple HealthKit/Android Health Connect e Garmin/Withings/Oura/Fitbit têm estado honesto de integração; framework não equivale a sincronização |
| UX-058 | P2 · 035, 042, 051–057 | Tendências, resultados e adaptação de objetivos | Estado diário/rolling estável, peso/atividade/adesão; ajustar estimativas só com evidência e revisão; energia de wearable não é automaticamente “comer de volta”; plano profissional não é ultrapassado |
| UX-059 | P2 · 008–011, 057, 060 | Caminho mobile/nativo, sincronização e preferências pessoais | Web responsiva primeiro; shell nativo e integrações quando necessários; conflitos/offline/retry explícitos; idiomas, unidades e timezone por contexto; identidade visual preservada |
| UX-060 | P0 antes de público · 001, 013, 017 | Autenticação, contas, papéis, autorização e partilha/consentimentos | Acesso validado no servidor; isolamento entre famílias/pessoas e partilha profissional explícita; UUID deixa de ser credencial; demonstração não transmite a ideia de proteção inexistente |
| UX-061 | P0 antes de público · 001, 003 | Segredos/vault, backup/restauro, retenção e observabilidade | Sem segredos/dados pessoais em cliente/logs/capturas; segredos revogáveis; backups restauráveis; logs sanitizados e erros correlacionáveis; registos sensíveis com acesso apropriado |
| UX-062 | P2 · 003, 007–008, 027, 038 | Desempenho e manutenibilidade orientados por medição | Reduzir carga inicial e dividir componentes/hooks sem duplicar estado; medir consultas e renderizações; índices apenas com evidência/EXPLAIN; paginação/caches com invalidação por versões |

## Fase 9 — Validação, integração e entrega

| ID | Prioridade / dependências | Tarefa e base a reutilizar | Conclusão observável |
|---|---|---|---|
| UX-063 | P1, contínua · 003–004 e cada fatia | Testes de componentes, E2E e regressão visual nas quatro resoluções | Testar resultados persistidos: família/pessoa, receita, presença, proposta, variante, compras/receção, tema/idioma/teclado; contexto mudado durante pedido e versão concorrente; dados sintéticos |
| UX-064 | P1, por etapa · 012, 024, 027, 038, 055 | Testes com pessoas e evidência académica | Sucesso, tempo, hesitações e compreensão registados; revisões documentadas; cenários construídos distintos de entrevistas/testes reais; materiais low/high e métricas IA atualizados |
| UX-065 | P1 por release · tarefas da release e 060–061 se público | Rollout progressivo, documentação, CI e comparação com protótipo | Feature flag por percurso quando útil; rollback visual/dados; zero funcionalidade perdida; API/Web CI no head exato; estado canónico atualizado; ferramentas académicas ocultas em produção |

## Rastreabilidade para todos os roadmaps existentes

### Quadro T01–T12 e roadmap familiar integrado

| Origem | Estado encontrado | Tarefas deste plano |
|---|---|---|
| T01 edição de propostas | Existe na branch | UX-019, 023–024 |
| T02 variantes completas | Existe na branch, não em main | UX-023–026 |
| T03 validação para presentes | Existe para contexto/regras suportadas | UX-015, 025, 029–035 |
| T04 presença/padrões/individual | Parcial; slot/cópia/repetição existem | UX-028–029 |
| T05 original/variante e escolhas fixadas | Parcial; dependências por contexto | UX-024–025, 030, 033–035 |
| T06 ingredientes efetivos/compras | Avançado: embalagens, receção parcial, validade | UX-037–043 |
| T07 catálogo/rótulos/retalho | Cobertura limitada e observada, não live | UX-020, 039–040, 043 |
| T08 pesquisa/mapa | Parcial; mapa no detalhe já existe | UX-044–046, 048 |
| T09 conectores reais | Depende de contratos/acessos | UX-045, 047–048 |
| T10 sobras/consumo/feedback | Consumo e eventos têm fundações; ciclo por completar | UX-031, 035–036, 042, 051–052 |
| T11 fases/tolerâncias | Por completar | UX-015, 025, 056 |
| T12 consolidação/revisão | Branch publicada; main por integrar | UX-001–004, 060–065 |
| Integração semanal por contexto | Grupo, data, regras e fontes | UX-027–035, 044–048 |
| Operação doméstica completa | Stock, reservas, efetivo/previsto, reversões | UX-037–043 |

### Roadmap de planos nutricionais e orientação

| Fase original | Tratamento neste revamp |
|---|---|
| 1 NutritionPlan + 2 EffectiveNutritionPlan | Preservar o domínio; UX-015–016, 025–026 |
| 3 importação/parser/revisão | Preservar caminhos existentes; UX-049–050, 053, 055 |
| 4 MealPlanFit | UX-025, 033–035 e mesmo avaliador em UX-048 |
| 5 transformação | UX-023–026, 030, 034 |
| 6 casa/despensa/receitas | UX-018–024, 032, 037–043 |
| 7 restaurantes/entrega | UX-044–048 |
| 8 planeamento adaptativo semanal | UX-027–036 |
| 9 feedback/aprendizagem | UX-042, 051–055, 058 |
| Catálogo confiável paralelo | UX-020–022, 039–043, 053 |

### Visão de produto e arquitetura

Person/Family/User, objetivos e porções: UX-013–017, 028–035, 060. Agenda e cozinha/equipamento: UX-029, 032, 056. Saúde, treino, outcomes e providers: UX-056–059. Aprendizagem de preferências e energia: UX-051–058. Idiomas/unidades/timezones/mobile: UX-008, 011, 014, 028, 059. Privacidade/consentimento/segredos: UX-017, 048, 057, 060–061. Acessibilidade, performance e operação: UX-005–011, 054, 062–065.

Nenhuma destas referências exige encher a home com todas as capacidades. As funcionalidades avançadas entram por contexto e detalhes progressivos.

## Primeiro incremento concreto após consolidar o baseline

1. UX-005 + UX-006: temas, marca e ícones aprovados, sem mudar regras ou cálculos.
2. Base de UX-007 + UX-008: componentes e navegação com URLs/contexto.
3. UX-009 + UX-010 + UX-012: home e avatares com resposta leve, incluindo movimento reduzido.
4. Fatia vertical UX-014 → UX-024 → UX-027 → UX-038, reutilizando APIs da baseline consolidada.
5. UX-063 em cada passo: dados persistem; restrições mantidas; quatro viewports; claro/escuro; sem regressão de compras/variantes.

**Demonstração de aceitação da primeira fatia:** uma família abre o novo início, escolhe um jantar da semana, identifica uma restrição individual, compara uma variante completa, aceita no mapa e vê as compras com os ingredientes efetivos. Ao retirar/adicionar a pessoa com a restrição, a avaliação e as porções são revalidadas. Avatares e transições reforçam a ação, sem substituir a explicação.

O resultado deve parecer o protótipo aprovado e comportar-se como a aplicação real. O motor demonstrativo do HTML, valores nutricionais ilustrativos e regras locais de compras não entram em produção.

## Definição de concluído por tarefa

- Nova estrutura, tokens e estados comuns aplicados à superfície alterada; claro/escuro e PT/EN verificados.
- Fluxo funcional com API real ou capacidade explicitamente indisponível; sem sucesso fictício.
- Segurança alimentar e autoridade dos cálculos no servidor preservadas; dados históricos e regras profissionais intactos.
- Estados de erro/vazio/pedido lento/concorrência, foco, teclado e movimento reduzido tratados.
- Testes apropriados e documentação da capacidade atualizados no mesmo incremento; evidência visual sintética identificada.
- Nenhum commit/merge por “concluir visualmente” se faltarem gates do repositório.

### Incremento: rascunhos com dados herdados em falta

UX-019/024/026: revisão final acessível mesmo com rendimento ou alternativas incompletos; pendências explícitas, guardar/retomar snapshot parcial persistido. Aplicação de variantes completas continua a exigir validação. Verificado com API real isolada, 177 testes web, 447 testes API e build.

### Edição da receita com os mesmos dados da base — 19 novembro 2026

UX-019/024/026: aceitar descrições e herdar quantidades, unidades livres existentes, rendimento ausente, preparação e porções sem novos dados obrigatórios. Persistência real de receita editada privada, distinção de validação nutricional, aplicação ao plano, compras e confirmação após reload. Nutrientes desconhecidos não são inventados. 182 testes frontend/build, 452 API, Ruff e E2E real isolado passaram; caso Frango da família principal verificado sem gravar escolhas.

### Lote de 20 tarefas — 19 novembro 2026

Ver [checklist e evidência](../ux/lote-20-2026-11-19.md): 20/20 concluídas localmente. Avança UX-008 (URLs/contexto), UX-018/019 (catálogo/editor), UX-009/031 (presenças e editor) e UX-063 (QA), sem declarar os IDs amplos concluídos ou integrados em main. 188 testes frontend/build, E2E real isolado e regressão de adaptação passaram. Não houve alteração de dados da família principal, commits ou publicação neste lote.
