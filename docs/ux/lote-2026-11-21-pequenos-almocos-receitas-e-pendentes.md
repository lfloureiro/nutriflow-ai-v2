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
- Duplicado «Frango rápido · família»: só um título duplicado foi demonstrado; não apagar automaticamente sem comparar composição, vínculos e histórico. Já existe `GET .../recipe-variants/duplicates` (read-only) e remoção lógica de receitas na UI.

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

## Versão do lote
- `apps/web/package.json`: **2.1.22**. Contém as correções documentadas de 21/11/2026 e a primeira revisão do UX de Receitas; não representa conclusão de paridade das outras páginas.
- Commits principais: `cef8ce5` (densidade do Início), `bc46d3b` (estado do filtro), `2a0dbbe` (UI do filtro), `dd5948d` (teste), `9593445` (atalho Sem imagem). Confirmar sempre último SHA e os 3 checks.

## Política de execução
Trabalhar em commits pequenos no PR #76, com testes e documentação por lote. Não declarar «pronto a testar» enquanto existir CI vermelho ou divergência visual conhecida. Atualizar este documento quando um item mudar de estado; não apagar histórico dos handoffs anteriores.
