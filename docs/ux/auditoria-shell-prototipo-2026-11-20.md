# Auditoria do shell comum — Casa à Mesa (20/11/2026)

## Fonte e método

- Fonte primária lida: `Casa_a_Mesa_High_Fidelity.html` da biblioteca do projeto (146 886 bytes).
- Comparação estática de regras CSS do protótipo com `apps/web/src/styles.css`, `shell.css`, `ux-foundation.css`, `design-tokens.css` e a árvore `App.tsx` da branch do PR #76.
- **Limite:** ainda não existe nesta execução uma recolha de `getComputedStyle` com os dois documentos abertos no mesmo Chrome, escala, viewport, fontes efetivamente carregadas e tema. Igualdade visual pixel a pixel **não está certificada**.

## Valores diretamente extraídos do protótipo

| Propriedade | CSS do protótipo |
| --- | --- |
| Fundo, claro / escuro | `#f6f5f0` / `#19191b` |
| Painel, claro / escuro | `#fffefa` / `#222225` |
| Texto, claro / escuro | `#25372d` / `#f1eeea` |
| Linha, claro / escuro | `#dedfd5` / `#414044` |
| Ação, claro / escuro | `#285a40` / `#d8b28c` |
| Acento decorativo, claro / escuro | `#e0a777` / `#d8b28c` |
| Corpo | `14px/1.55 'DM Sans',sans-serif` |
| Títulos | `Manrope,sans-serif` |
| Barra lateral | `230px`, `padding:34px 20px 22px`, `gap:36px` |
| Marca | `36px` quadrado, raio `12px`; nome `700 19px Manrope` |
| Navegação | `gap:5px`, botão `padding:12px 14px`, raio `11px`, peso `550` |
| Cartão IA | `padding:15px`, raio `14px`, fundo `var(--bg)` |
| Cabeçalho | `height:92px`, linha inferior `1px solid var(--line)` |
| Mapa semanal | `70px + 7 colunas`, `gap:7px`, células `min-height:112px`, raio `11px` |
| Sombra tema escuro | `none` |
| Sombra tema claro | `0 16px 50px #2736230b` |

## Alterações do primeiro lote

1. Retirados de `shell.css` os estilos da navegação e cabeçalho condicionados por `.app-shell--meals`; mantidas somente regras particulares do conteúdo da Semana.
2. Criado `shell-prototype.css`, importado **depois** dos estilos de ecrã para preservar a precedência do shell global e aplicável a todas as rotas desktop.
3. Alinhados `styles.css` e os tokens com as famílias e as cores declaradas no protótipo. Adicionada carga explícita de DM Sans e Manrope por Google Fonts, com fallback `sans-serif`.
4. Preservados os seis destinos, o cartão IA, o indicador de versão, os drawers e o motor funcional da carta «Próxima refeição». Não houve mudanças na API ou base de dados.

## Verificações e pendências

- As famílias tipográficas **são declaradas**, mas o ficheiro HTML original não contém um `@font-face` nem importação de Google Fonts; a fonte realmente utilizada no protótipo depende da instalação do computador. Confirmar `document.fonts.check` e `getComputedStyle` antes de declarar paridade de renderização.
- Verificar rotas `home / meals / house (recipes + pantry) / people / shopping / more`, claro e escuro, a 1440/1024/768/390 e zoom 200%. No mobile a sidebar desaparece e é substituída pela navegação inferior, que tem contrato próprio.
- A equivalência de cartões, ícones, fotografias, hero e grelha semanal carece de auditoria por ecrã. Não alterar cores ou valores específicos só por comparação de screenshots.
- Verificar Web CI, API CI e UX E2E **no mesmo SHA final**, não transpor o verde da v2.0.73 para este lote.
- PR #76 deve permanecer draft; não fazer merge para `main`; dados reais, backend local e serviços em execução não foram tocados.

## Segundo alvo: composição visual aprovada, v2.0.75

A captura fornecida pelo utilizador nesta sessão (20/11/2026, 1536 × 1024) é o **alvo de aceitação da composição Semana**, que não é exatamente o HTML high-fidelity original: nela existem gradientes, iluminação âmbar, cartão AI mais luminoso, ícones e tipografia maiores, uma faixa informativa que foi posteriormente retirada por decisão explícita, e proporções revistas. A faixa não deve ser restaurada; o conteúdo operacional e a carta «Próxima refeição» prevalecem sobre textos demonstrativos da imagem.

Amostras da imagem, medidas como **medianas RGB de regiões sem texto**, com coordenadas relativas à captura (não são necessariamente valores CSS em bruto, porque podem representar sobreposição de gradientes, transparência e antialiasing):

| Zona amostrada | RGB observado |
| --- | --- |
| Sidebar topo | `(30,30,32)` |
| Sidebar centro | `(31,30,32)` |
| Sidebar base | `(29,28,32)` |
| Canvas topo | `(22,22,24)` |
| Canvas inferior | `(20,20,23)` |
| Navegação ativa esquerda/direita | `(87,65,45)` / `(81,60,44)` |
| Cartão IA esquerda/direita | `(60,51,43)` / `(35,33,36)` |
| Painel semanal alto/baixo | `(31,31,34)` / `(26,26,28)` |
| Célula normal / por adaptar | `(27,27,30)` / `(75,47,41)` |
| Dia selecionado / badge | `(76,60,48)` / `(104,73,37)` |

Escalas observadas aproximadamente: limite da sidebar em x≈320, hero horizontal com altura ≈137px, painel semanal de x≈345 a x≈1517, cabeçalho de dias ≈83px, linhas de refeição ≈133px. **São medições da imagem de referência**, não confirmação do CSS calculado da aplicação.

Implementação desta aproximação geométrica/óptica fundamentada: `shell-prototype.css` (todos os ecrãs desktop, sidebar 320px acima de 1300px, gradientes e brilho dark) e `week-reference.css` (somente a semana, hero, grelha, células, tipos de estado, sombras e badges), ambos importados após folhas históricas. Mantêm-se o HTML React, drawers, dados e semântica atuais.

**Gate obrigatório antes de dizer EXATAMENTE igual:** carregar o HTML original, a imagem alvo e a app no mesmo Chromium e confrontar, por viewport e por tema, screenshot de imagem + `getComputedStyle` das classes pertinentes. O CSS é uma transcrição controlada dos valores visíveis, mas não dispomos ainda da screenshot da aplicação v2.0.75 na mesma configuração; a igualdade exata não está demonstrada. Os cartões reais têm conteúdo variável, ao contrário do mockup. Os textos e a data do screenshot são apenas ilustração.

## Verificação da aplicação real através de capturas (20/11/2026, 23:06–23:07)

Recebidas duas capturas da app **v2.0.75** (imagens originais 1920×1200, com barras do Chrome/Windows) e a composição aprovada (1536×1024, apenas interface). As capturas não estão em coordenadas comparáveis por diferenças de janela, browser chrome, escala e região visível: **não calcular pixel-diff bruto entre os PNG completos**.

Factos visíveis nas capturas reais: a sidebar e a topbar têm o mesmo estilo nas duas posições de scroll; o cartão IA e a navegação apresentam gradiente e destaque âmbar. A app mostra **estado real e honesto** da carta seguinte («Nenhuma proposta elegível confirmada») e utiliza ilustração fallback, porque não há fotografia real da refeição seguinte. Não substituir por «Salmão» ilustrativo apenas para fingir fidelidade ao mockup. A grelha contém a semana real, com espaços vazios e estados «Planeada», «Por verificar» e «Adaptação aplicada». O cabeçalho global, navegação entre semanas e barra de tarefas presentes na captura real não existem na composição ilustrativa.

Diferença funcional importante: a imagem da referência mostra uma carta de sugestão estática, mas o produto aprovado usa a carta **«Próxima refeição» dinâmica** e não inventa recomendações. A fidelidade exata aplica-se a contornos, proporções, imagem quando existir, layout, luz, cor e tipografia, não à identidade de dados irreais.

Defeitos concretos encontrados:
- A imagem `/images/shared-meal.svg` estava a controlar a altura intrínseca da grelha do hero, deixando o cartão maior do que o alvo. A regra desktop em `week-reference.css` fixa 136px também na imagem para impedir expansão.
- O Web CI v2.0.75 anterior falhou em dois testes novos por importações `?raw` de CSS vazias no Vitest, não por falha funcional. `shellPrototype.test.ts` foi corrigido para ler os ficheiros por `node:fs`.
- Testes, screenshot da app com **viewport de conteúdo 1536×1024**, escala 100%, fonte carregada em dark/light e medição de `getComputedStyle` continuam obrigatórios para afirmar igualdade.

## v2.0.76 — cascata determinística + medição real em Chromium

- A inspeção do Web CI da versão anterior confirmou **234 testes Vitest aprovados**, mas falha do TypeScript por falta de declarações de `node:fs` no teste de leitura CSS. Adicionada supressão de tipo apenas ao import de teste, sem novos pacotes ou mudança da build da aplicação.
- Os estilos `next-meal-hero.css` e `weekly-matrix.css` eram importados em componentes React lazy; a injeção tardia de CSS podia substituir a folha de referência por ordem de carregamento. Movidos ambos os imports para `main.tsx`, imediatamente antes de `week-reference.css` e `shell-prototype.css`. Removidas as importações duplicadas dos componentes, sem alterar JSX ou comportamento.
- A captura real enviada pelo utilizador evidenciou uma diferença de escala entre a resolução física da captura (1920×1200, barras do navegador incluídas) e o viewport CSS efetivo. Aplicada largura de menu `clamp(230px,20.833vw,320px)` para CSS viewport ≥1101px, em vez de ativação só a 1300px, e a mesma fronteira para a geometria desktop da grelha e hero.
- Novo teste sintético Playwright `e2e/shell-visual-parity.spec.ts`: lê `getComputedStyle` real do menu, marca, tile AI, família e topbar em seis destinos em light/dark; verifica largura proporcional, fonte, sete dias × quatro tempos e altura da carta, sem escrever na família verdadeira.
- O CI `ux-e2e.yml` passa a guardar três screenshots **com dados sintéticos** (desktop dark, desktop light e mobile light), como artefacto `week-visual-<SHA>`, para inspeção ótica e comparação posterior. CI 3/3 e inspeção dos PNG ainda obrigatórios no **último SHA**, não transferir o resultado de commits anteriores.
- A referência visual final continua a ser a captura composta aprovada pelo utilizador; a fonte de dados e a lógica dinâmica da «Próxima refeição» não são substituídas por conteúdo da imagem. A Semana **não está automaticamente pronta** apenas por testes sintéticos; comparar imagens e requerer aprovação visual do utilizador. PR #76 permanece draft.

## v2.0.77 — rodapé familiar + qualidade responsiva

- A imagem aprovada exibe no rodapé da sidebar um avatar circular, o nome da família e «Gerir o nosso espaço». O código anterior mostrava apenas «FAMÍLIA» e nome. `App.tsx` passa a usar botão acessível que abre a vista `more`, inicial da última palavra do nome real e legenda localizada PT/EN, **sem alterar os dados**. `shell-prototype.css` fixa avatar, gradiente, tipografia e sombra em light/dark.
- A tipografia da marca, navegação e tile AI varia via `clamp()` no intervalo 1101–1536 CSS px para evitar corte ou overflow quando existe escala de Windows.
- Novo Playwright `week-responsive-visual.spec.ts`: verifica ambos os temas e larguras 1440/1024/768/720/390, navegação lateral/inferior e inexistência de overflow horizontal; usa apenas família sintética no CI. `shell-visual-parity.spec.ts` também verifica que o rodapé abre Definições sem alterar o computed style da sidebar.
- Exigir 3/3 CI verdes no **último SHA**, olhar para screenshots sintéticas da semana e confrontar com a referência aprovada antes de pedir revisão humana. A captura final deve conservar as diferenças **funcionais** intencionais (semana e receitas reais, aviso verídico de elegibilidade, barra global e acesso de datas).
- PR #76 mantém-se draft, sem merge; API, dados familiares reais, processos de desenvolvimento em Windows e PostgreSQL local intocados.

## v2.0.78 — problemas efetivamente observados nos PNG do Chromium

- A v2.0.77 (SHA `89594ce7d2b6f0279cb45decb508972c116e447d`) terminou com **3 CI verdes no mesmo commit**. O artefacto `week-visual-8a9137d6203da1474fa397d9422dfad66ac5c18b` contém screenshots sintéticas (1440 dark/light, 390 light).
- A leitura direta dos PNG confirmou problemas que asserções de altura não detetavam: texto da carta «Próxima refeição» cortado no topo quando há mensagem longa; rodapé familiar parcialmente escondido em desktop com altura 900px; aviso redundante «São necessárias duas pessoas» acima da grelha com um único membro; disclosure «Resumo do dia selecionado» ainda apresentado no modo semanal simples.
- **Correções v2.0.78:** art do hero em posição absoluta dentro da coluna visual e imagem sem tamanho intrínseco a controlar a grid; carta com altura mínima 136px mas crescimento pelo texto para não cortar informação; sidebar com scroll seguro e densidade reduzida em janelas desktop ≤950px de altura; aviso de duas pessoas no mapa simples omitido somente quando a carta já o explica (uma pessoa), preservado quando não existe ninguém; disclosure do dia oculto apenas no modo simples, permanecendo nos modos legados. Os drawers, ações e dados continuam acessíveis.
- O teste de geometria passa a confirmar que a informação do hero está integralmente dentro do cartão, em vez de exigir altura rígida 136px que cortava texto; screenshots sintéticas forçadas a PT-PT para comparação com a referência. Testes Web/API/E2E **novamente obrigatórios no SHA final v2.0.78**, pois os verdes eram da v2.0.77.
- Continuam diferenças intencionais entre a composição ilustrativa e a aplicação real: datas e pratos do agregado, estado correto da recomendação e toolbar global. **Não declarar pixel-perfect nem pedir aceitação final** sem nova comparação visual após os gates.
