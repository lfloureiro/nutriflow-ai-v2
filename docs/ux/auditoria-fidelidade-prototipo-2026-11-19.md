# NutriFlow AI v2 — auditoria de fidelidade ao protótipo Casa à Mesa

**Referência visual/funcional:** `Casa_a_Mesa_Prototipo.html` (protótipo high-fi aprovado em 18–19/11/2026); decisões do chat de ideação e do desenvolvimento de 19/11; backlog existente e `docs/handoff-2026-11-19.md`.

**Regra vinculativa:** os cinco destinos principais (Início, Refeições, Pessoas, Casa/Receitas, Mais) são páginas de navegação. **Detalhe de um objeto, criação, edição, avaliação e adaptação devem abrir uma única aba lateral contextual**, mantendo a grelha ou lista que lhes deu origem. Fechar fecha apenas essa aba e devolve foco ao acionador; não abre a vista anterior em cascata. Não sacrificar capacidades reais de NutriFlow v2 em nome da semelhança estética.

## P0 — desvio de navegação confirmado; fix incluído na v2.0.24

| Origem | Problema identificado no código | Regra restaurada |
|---|---|---|
| Semana, refeição existente → Alterar | O pai voltava a selecionar a refeição ao abrir editor, com potencial de duas abas simultâneas e fecho em dois passos | Limpar seleção e URL do detalhe antes de montar editor, **um dialog de cada vez** |
| Semana, slot vazio | Tratamento especial na grelha e outro no resumo do dia, com experiências diferentes | Ambos os pontos entram diretamente no editor de refeição, numa única aba |
| Casa → Receitas → abrir/criar/copiar | Catálogo deixava de existir na árvore ao selecionar receita; editor ou viewer surgia em lugar da lista | Preservar catálogo e renderizar detalhe/editor num `ContextDrawer` |
| Casa → Ingredientes → abrir/criar | Mesma substituição da lista pelo editor | Preservar lista e renderizar editor num `ContextDrawer` |
| Pessoas → pessoa | `PersonOverview` substituía a lista de pessoas por um ecrã completo | Manter lista atrás de `ContextDrawer` com perfil e subsecções |
| Pessoas → adicionar | Formulário era inline na lista | Abrir `PersonSetupForm` num `ContextDrawer` |

**Regressão automática acrescentada:** Playwright confirma uma única modal em cada fluxo, persistência da lista/grelha em background e fecho direto; dados fictícios apenas com PostgreSQL temporário. A execução no SHA final é necessária antes de declarar o fix validado.

## P1 — verificação explícita necessária ANTES de chamar v2.1.0 de pronta

- Avaliar diferenças restantes entre os percursos de **Início → Refeição**, **Refeições → Hoje/Semana**, **Pessoas → perfil/saúde/nutrição**, **Casa → Receitas/Ingredientes/Despensa**, **Compras** e **Mais**: ações detalhadas não podem substituir indevidamente a página principal.
- Distinguir em cada ação **página principal**, **drawer**, **separador dentro do drawer** e **confirmação**; documentar o destino de Escape, botão Voltar e histórico do browser.
- Verificar em dispositivo real desktop/mobile os estados com refeição **existente**, **proposta**, **vazia**, **em revisão** e **adaptada**. Evitar abrir um resumo expandido por trás do drawer e impedir aberturas em cadeia.
- Garantir que o drawer tem uma única região rolável, botões de ação acessíveis, foco seguro, proteção de rascunhos e estilo consistente; testar com zoom real 200%.
- Revisitar formulários de subáreas ainda inline (despensa, compras, fontes, preferências e revisão alimentar) caso representem **detalhes/edições** em vez de páginas/áreas de navegação.
- Reavaliar visual do mapa semanal: densidade, hierarquia dia/tempo, botões, propostas, vazios, selecionados e adaptações, comparando com o high-fi em 1440/1366/768/390 e ambos os temas; testes E2E de scroll sem screenshots comparativas não bastam.

## P1 — funções exigidas pelo utilizador, SEM REMOÇÕES

- Dashboard familiar e contexto do tempo de refeição; mapa com **pequeno-almoço, almoço, lanche e jantar**.
- Família, perfis, utilizadores/contas e gestão de perfis.
- Criação/edição de receitas e ingredientes, variantes, substituições e proveniência.
- Avaliação de refeições **nutricional**, **FODMAP com incerteza/porção**, **estrelas 1–5 por pessoa** e score familiar separado; restrições obrigatórias nunca são ultrapassadas por estrelas.
- Adaptação/transformação de receitas por pessoa e para a refeição escolhida; guardar e confirmar explicitamente; original preservado.
- Despensa e lista de compras com estados distintos (disponível, a comprar, comprado e recebido, conforme contrato).
- Português/inglês, dark/light/sistema e responsive.

## P2 — não declarar concluído sem evidência funcional

- Integração de nutrição com planos profissionais e orientações com fontes e datas; não inventar nutrientes ou regras clínicas.
- Padrões semanais e exceções de presenças, convidados, sobras e consumo registado; conferir impacto em porções e compras.
- Importação de receitas via texto/URL e revisão de extração; futura vertente ML/NLP treinada e avaliada, não apenas heurísticas.
- Segurança/autenticação/autorização por família, consentimentos, backups e observabilidade antes de disponibilizar publicamente.

## Política de entrega

1. **P0 de comportamento antes de novos patches cosméticos.** Regressões verificam a experiência aprovada, não apenas classes CSS ou presença de componentes.
2. Não declarar v2.1.0 pronta sem gates Web CI/API CI/UX E2E **verdes no mesmo SHA**, inspeção visual real e testes manuais de aceitação.
3. Continuar no PR #76 draft; não fazer merge para `main` nem tocar dados familiares reais.
