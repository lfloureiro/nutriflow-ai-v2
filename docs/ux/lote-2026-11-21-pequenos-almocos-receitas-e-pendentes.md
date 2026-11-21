# NutriFlow AI — continuidade UX e recomendações (21/11/2026)

## Autoridade e proteção
- Repositório `lfloureiro/nutriflow-ai-v2`, PR #76, branch `codex/ux-drawer-next-batch-20261119`. Não alterar `main`, não modificar a base de dados real e não fazer merge.
- Ler também `docs/handoff-2026-11-21-home-v2.1.17.md`, `docs/ux/auditoria-shell-prototipo-2026-11-20.md`, `docs/ux/auditoria-critica-imagens-aprovadas-2026-11-21.md`, `docs/ux/receitas-imagens-e-deduplicacao-2026-11-21.md` e `docs/ux/references/manifest.json`.
- A Semana foi aprovada visualmente. Não reescrever a grelha; conservar o shell global e os drawers, dark/light e mobile. Os mockups são referências visuais, não fonte de ingestão nem de refeições inventadas.

## Pequeno-almoço sem recomendação — diagnóstico e limite
Captura real de 21/11/2026 às 20:52: o hero da Semana mostra a próxima refeição de **domingo 22/11, 08:30, pequeno-almoço**, mas «Nenhuma proposta elegível confirmada». A seleção temporal está correta; não há prova de inexistência de receitas. Existe um seed de desenvolvimento com **11 receitas** em `apps/api/app/development_breakfast_seed.py`, mas não há acesso à BD local para confirmar se foi aplicado e quais são os bloqueios de cada pessoa.

- O hero carrega `getRecommendationBootstrap(firstPerson, slot.scheduledAt, {ensureState:false})`, filtra por `suitable_meal_types === breakfast` e envia os candidatos ao planeador familiar. Se não existir candidato, o frontend anteriormente mostrava a mesma mensagem que um conjunto totalmente rejeitado.
- `weekly_planning_api.py` anteriormente devolvia motivos de `evaluation.exclusion_reasons`, omitindo motivos presentes só em `plan_fits`. Foram acrescentadas etiquetas de segurança, conflitos, regras e guidelines à saída `skipped_slots.exclusion_reasons` quando não há candidatos elegíveis.
- `NextMealBanner.tsx` distingue um conjunto vazio de candidatos de propostas avaliadas mas bloqueadas; `nextMealSelection.ts` traduz os tipos de bloqueio em PT/EN sem exibir IDs técnicos e sem relaxar regras obrigatórias. Teste em `nextMealHero.test.ts`.
- Sem API/BD real, **a seleção de uma receita para a manhã seguinte não está ainda demonstrada**. Próxima etapa funcional: inspecionar na família de desenvolvimento, não na BD real em produção, o bootstrap do primeiro perfil, presença dos 11 pequenos-almoços, `selected_plan`/`skipped_slots` e restrições da família; criar caminhos de adaptação seguros quando o catálogo não oferece opção comum. Não inventar recomendações nem ignorar restrições alimentares.

## Imagens e receitas
- A branch contém já **18 WebP** em `apps/web/public/images/generated/`, confirmados pela árvore GitHub; documentação anterior que afirma que só `bifanas-com-natas.webp` está no Git tornou-se histórica.
- `apps/web/scripts/verify-generated-images.mjs` validava o hash da **miniatura antiga** das bifanas (4 962 bytes) apesar de a imagem atual ter 71 076 bytes. O Web CI falhava por esse motivo. Corrigido: agora percorre todas as imagens locais WebP e verifica cabeçalhos, comprimento e formato; não prende um ficheiro a um hash histórico.
- Geração automática via OpenAI em `recipe_image_generation.py` já existe, depende de chave e armazenamento persistente; confirmar se a nova imagem é consultada depois do processamento. 18 imagens não cobrem todas as 69 entradas do PDF da família.
- `RecipeCatalogue` tem filtro de imagens **Todas / Com imagem / Sem imagem**, aplicado por correspondência de nome de prato exata via `resolveMealHeroImage` e conservado no estado da navegação. Há também atalho **Sem imagem (N)** na barra de resultados, com `aria-pressed` e comutação do filtro. Testes para o sufixo «· família». Objetivo: inspeção direcionada das receitas que ainda precisam de ilustração.
- Duplicado «Frango rápido · família»: só um título duplicado foi demonstrado; não apagar automaticamente sem comparar composição, vínculos e histórico. O catálogo passou a consultar `GET .../recipe-variants/duplicates` (read-only) e apresenta **Adaptações possivelmente duplicadas**, com nomes, IDs abreviados e acesso a cada receita. O editor dispõe de remoção lógica com confirmação, mas a auditoria em si não elimina dados.

## Correção de densidade do Início
No SHA `92b2d86`, Web CI e API CI passaram; UX E2E falhou no teste `shell-visual-parity.spec.ts`, em light e dark, com cartão de refeição medindo **373,984375px**, acima do contrato de 370px (1280×700). Em `home-v3.css`, a linha de ações/planos no layout de altura compacta passa de 165px para 177px, libertando espaço vertical do cartão do meio. Não reduzir as expectativas do teste. Revalidar 3/3 CI **no SHA final**, incluindo inspeção de geometria/contraste nos screenshots do CI.

## Fila UX — estado observado e próxima prioridade
1. **Início:** preservar composição editorial atual; validar 4 refeições, 4 barras, hero, densidade 1280×700/1280×631 e 390×844, valores estimados marcados, sem falsear consumo e sem overflow. O E2E de densidade é gate obrigatório.
2. **Receitas — em execução:** navegação/drawer e ação de apagar com histórico; filtro de cobertura de imagem introduzido neste lote. Pendentes: revisão lado a lado com `receitas.png` aprovado, cartões, tipografia, cores, carregamento de imagens recém-geradas, revisão de duplicados concretos. Não gerar receitas iguais ao adaptar.
3. **Família:** comparar com `familia.png` aprovado, gestão de perfis e avatares, avaliações de receitas por pessoa, diferentes estados de dados, mobile, sem perda funcional.
4. **Compras:** comparar com `compras.png` aprovado, ações checked/disponibilidade, produtos, fluxos de lista e drawers, mobile.
5. **Despensa:** comparar com `despensa.png` aprovado, stock e ligação a compras/receitas, edição e estados vazios, mobile.
6. **Cross-screen:** garantir um único shell partilhado (menu/topbar), tokens e fontes DM Sans/Manrope, seletores por tema, drawers laterais consistentes, i18n PT/EN e acessibilidade de teclado.
7. **Fotos pendentes:** identificar as restantes receitas a partir do catálogo real e gerar imagens fiéis, sem associar imagens de pratos diferentes; preservar autoria/proveniência e hashes para assets editados.
8. **Qualidade:** usar capturas reais e artefactos do Playwright para paridade com as cinco referências aprovadas; três CI verdes no mesmo SHA não equivalem a aprovação visual.

## Referências visuais recuperadas e verificadas

Os cinco PNG de referência **originais** foram localizados na Biblioteca do projeto, todos a 1672 × 941 pixels. Hashes SHA-256 verificados sem alterar os ficheiros:
- `inicio.png`: `9d4537597267bebdeaadadb1bc35d13f236e231b077354b3664caac830beec15`
- `receitas.png`: `8640d165073d827e84e31d589f49671e9f29aa324323798b836235d6704376c1`
- `familia.png`: `1c9be23e06a0f93c32ccbce5e567d61d6e63e0838d23b8e32bf0675f2af3c009`
- `compras.png`: `1593f11dd93c9121d6382c9800bc5800ad2b48a45fd375c377ca5fb2375f82d6`
- `despensa.png`: `2c83ee7034e955c8b8b682c3fc5722626b73543d0755b39e9151df5e27290135`

Em Receitas, a referência aprovada mostra um hero horizontal com receita real e painel de sugestões, uma pesquisa compacta, filtros rápidos e uma grelha de 4 colunas no desktop. O catálogo já tem hero/aside/grelha; **não preencher o painel com afirmações falsas de compatibilidade, tempos de confeção ou favoritos** só para reproduzir o mockup. Foram adicionados filtros rápidos visíveis Todas / Pequeno-almoço / Almoço / Lanche / Jantar / Adaptações, com estado acessível `aria-pressed` e versão mobile horizontal; os filtros avançados continuam em disclosure secundário. A auditoria de duplicados também continua secundária, sem alterar o catálogo.

Em Família, Compras e Despensa, as referências foram agora verificadas, mas ainda falta confrontar o browser atual, nos mesmos viewports, com cada imagem antes de implementar grandes mudanças visuais. Uma captura ilustrativa não é fonte de números reais de stock, preço, objetivos ou restrições.

## Versão do lote
- `apps/web/package.json`: **2.1.22**. Contém as correções documentadas de 21/11/2026 e a primeira revisão do UX de Receitas; não representa conclusão de paridade das outras páginas.
- Commits principais: `cef8ce5` (densidade do Início), `bc46d3b` (estado do filtro), `2a0dbbe` (UI do filtro), `dd5948d` (teste), `9593445` (atalho Sem imagem), `61df8d9` (cliente da auditoria), `9b6d4e5` (secção de duplicados), `0195deb` (filtros rápidos), `ecbdda1` (estilo responsivo). Confirmar sempre último SHA e os 3 checks.

## Política de execução
Trabalhar em commits pequenos no PR #76, com testes e documentação por lote. Não declarar «pronto a testar» enquanto existir CI vermelho ou divergência visual conhecida. Atualizar este documento quando um item mudar de estado; não apagar histórico dos handoffs anteriores.

## Substituição automática de leite — lote de 21/11/2026

**Pedido:** não descartar uma receita familiar de pequeno-almoço por conter leite meio-gordo se existe uma substituição viável; pesquisar bebidas alternativas, adicioná-las ao catálogo de ingredientes e propor a adaptação na Semana com ingrediente e substituto claramente identificados. Reutilizar o fluxo existente de transformação de refeições; não gerar outra receita familiar duplicada.

**Pesquisa externa (catálogos oficiais em 21/11/2026):**
- Continente: [bebida vegetal de arroz sem adição de açúcar](https://www.continente.pt/supermercado/laticinios-e-ovos/bebidas-vegetais-e-vegegurtes/bebida-arroz/), [aveia sem açúcar Alpro](https://www.continente.pt/produto/bebida-vegetal-de-aveia-sem-acucar-alpro-8152828.html).
- Auchan: [arroz com coco sem adição de açúcares](https://www.auchan.pt/pt/alimentacao/produtos-lacteos/bebidas-vegetais/arroz/bebida-arroz-coco-auchan-sem-adicao-de-acucares-sem-gluten-1l/3656235.html), [catálogo geral](https://www.auchan.pt/pt/alimentacao/produtos-lacteos/bebidas-vegetais/).
- Monash University: [alternativas ao leite](https://monashfodmap.com/blog/dairy-alternatives-beverage-and-yoghurt-low-fodmap-options/): leite de arroz é opção possível, mas bebida de aveia pode ser low FODMAP só numa porção menor; o rótulo «sem lactose» não demonstra adequação global. Não tratar a pesquisa como confirmação individual de alergias, FODMAP ou nutrientes.

**Implementação:**
- `development_plant_milk_seed.py` adiciona **ingredientes genéricos, não produtos comerciais certificados**: bebida de arroz, bebida de aveia, bebida de arroz/coco e leite sem lactose. Reutiliza `breakfast:ingredient:milk` da receita original, sem criar um segundo ingrediente «leite».
- Regista `FoodTransformationProfile` por família sob `milk-for-breakfast` e composições **ilustrativas/provisórias** para viabilizar apenas testes de desenvolvimento. As estimativas por 100 ml não vêm de rótulos verificados e devem ser substituídas por composições reais antes de recomendações nutricionais em produção.
- Bebida de arroz e leite sem lactose entram como candidatos automáticos **ainda sujeitos à avaliação completa por pessoa**. Aveia e arroz/coco são alternativas registadas mas com `auto_transform_enabled=false` até confirmação de composição, porção e restantes restrições.
- `development_seed.py` chama o novo seed idempotente para as famílias de desenvolvimento e inclui os perfis no fluxo existente. **Só aparece na instalação depois de voltar a executar explicitamente o seed de desenvolvimento ou aplicar estes dados por outro processo apropriado; um git pull sozinho não modifica a BD.** Não executar sobre dados reais sem ordem do utilizador.
- `shared_meal_transformation.py` reconhece agora a recuperação de elegibilidade como motivo de proposta, mesmo que não haja melhoria da pontuação de preferência. `weekly_planning_api.py` volta a considerar variantes para receitas inicialmente rejeitadas, aumentando o limite por receita de 3 para 8 e reavaliando segurança/nutrição dos participantes. `NextMealBanner.tsx` mostra «Adaptação proposta — ingrediente a trocar: leite → bebida ...» e o fluxo de confirmação mantém o `MealTransformationApplication` do calendário (sem criar nova receita).
- Teste de catálogo valida idempotência e duas variantes automáticas sem ativar aveia/coco como universalmente seguras.

**Limitações importantes:** o motor usa alternativas presentes no catálogo verificado/persistido, não executa uma pesquisa web em tempo real dentro de cada recomendação. Uma pesquisa na loja deve alimentar um catálogo de ingredientes e composições verificadas; não associar automaticamente SKU a estimativas genéricas. O almoço/jantar/lanche já usam o mesmo algoritmo de substituições, condicionado à existência de perfis e evidência suficiente. Uma só substituição pode ser insuficiente quando vários ingredientes estão bloqueados; múltiplas operações simultâneas precisam de desenvolvimento adicional. Não prometer uma proposta elegível antes de validar com os dados familiares.
