> Referência de continuidade: [estado atual e próximas tarefas](../handoff-2026-11-19.md). Registos intermédios abaixo são históricos; o fluxo atual está em aceitar-trocas-e-refeicao.md.

# Direção visual e de interação do NutriFlow AI

Referência aprovada em 18 novembro 2026: protótipo único `Casa_a_Mesa_Prototipo.html`. Este contrato acompanha o [backlog de transformação](../vision/ux-revamp-task-board.md) e aplica-se à app real, sem transportar dados ou cálculos demonstrativos.

## Identidade e temas

Nome principal **NutriFlow AI**, peso visual forte. Subtítulo **Casa à Mesa**, menor e discreto. Mesma hierarquia no desktop, mobile, entrada da família e materiais de apresentação. Não usar “by NutriFlow AI”.

| Token semântico | Claro | Escuro |
|---|---|---|
| Fundo | `#f6f5f0` | `#19191b` |
| Superfície | `#fffefa` | `#222225` |
| Superfície secundária | `#eeeee6` | `#2d2c2f` |
| Texto principal | `#25372d` | `#f1eeea` |
| Texto secundário | `#697569` | `#b0aaa4` |
| Separador | `#dedfd5` | `#414044` |
| Ação / seleção | `#285a40` | `#d8b28c` |
| Ação suave | `#e5eddf` | `#39312c` |
| Atenção | `#855018` em `#faecd9` | `#e4bc83` em `#3b3023` |
| Conflito | `#994a39` em `#f9e6df` | `#e6a494` em `#402b29` |

Transportar para nomes semânticos (`--color-bg`, `--color-surface`, `--color-action`, `--color-text`, etc.), sem perpetuar `--green` para representar âmbar. Rever cada par texto/fundo no tamanho de utilização real. Estado não depende só de cor: texto, ícone e motivo são necessários. Não impor a paleta da marca a alimentos fotografados ou a fontes externas.

Os tokens de foco devem ser suficientemente contrastantes nos dois temas. Tema Claro/Escuro/Sistema é uma escolha explícita e persistente; a preferência Sistema acompanha mudanças do sistema. Testar variáveis CSS, fundo computado de html/body, controlos e overlays, não apenas o valor do seletor. O bug encontrado no empacotamento académico torna este teste obrigatório na regressão.

## Estrutura e densidade

- Desktop: navegação lateral compacta, máximo de largura legível, grelha de semana própria e painel lateral de detalhe.
- Tablet/mobile: cinco destinos principais; semana por dia e quatro refeições visíveis; painel de detalhe ocupa o ecrã quando necessário.
- Home: próxima refeição, decisões pendentes e resumo familiar. Sem painéis densos de saúde ou métricas decorativas.
- Listas: linhas compactas; cartões com imagem quando ajudam a escolher receitas, não para todos os campos.
- Formulários: identidade/necessidades primeiro; medições, fontes comerciais e detalhes avançados depois. Rascunhos preservados ao acrescentar linhas, mudar separador ou regressar.
- Ícones SVG consistentes; evitar caracteres Unicode que mudam de proporção conforme o sistema.
- Fontes com fallback local, hierarquia confortável e conteúdo principal normalmente entre 14–16 px. Legendas pequenas não devem suportar decisões críticas.
- Barras de scroll podem ser ocultadas na app conforme a preferência aprovada; preservar roda, touch, teclado e foco visível. Dar pistas de continuidade quando o conteúdo prossegue. Nunca usar `overflow:hidden` na página para esconder cortes de layout.

## Avatares com presença e resposta

Criar um componente `PersonAvatar`, reutilizado em família, refeições, porções e feedback. A identidade tem cor/forma persistente, alternativa de iniciais e, futuramente, ilustração ou fotografia escolhida. Não usar os Pets do ChatGPT como dependência da app.

| Estado | Representação | Movimento proposto |
|---|---|---|
| Normal | Avatar estático e nome acessível | Nenhum loop automático |
| Hover/foco | Contorno e contraste de seleção | Escala até 1,03, 120–160 ms |
| Selecionado | Contorno estável e marca de seleção | Confirmação única de 160–200 ms |
| Participa | Marca e nome no grupo da refeição | Entrada suave de 160–200 ms |
| Não participa | Estado textual disponível no editor | Saída de 120–160 ms, sem ocultar a decisão |
| Por confirmar | Marcador específico e legenda | Sem piscar ou pulsar continuamente |
| Porção alterada | Valor atualizado junto da pessoa | Destaque de 180–220 ms no valor, não no corpo todo |
| Guardado | Confirmação visível | Pequeno aceno/realce único, até 220 ms |

Estes tempos são a especificação inicial, a validar no protótipo integrado. Preferir `transform` e `opacity`, sem movimentar layout ou introduzir uma biblioteca pesada apenas para um efeito. Ilustrações SVG podem ter pequenas expressões, mas não devem comunicar diagnóstico, gravidade clínica, culpa ou uma certificação alimentar por expressão facial.

Com `prefers-reduced-motion: reduce`, manter os mesmos estados sem movimentos de escala/deslocação. Acessibilidade, foco e seleção não dependem da animação. O avatar não substitui o nome ou o checkbox. Não mostrar uma reação feliz por um conflito ter sido parcialmente resolvido se a avaliação continua pendente.

## Movimento dos fluxos

Painéis abrem/fecham em 180–220 ms; a seleção do dia ou separador usa transição breve, sem perder foco. A alteração aceite destaca a célula certa no mapa semanal uma vez. Compras atualizadas mostram o resultado, a diferença e eventual aviso; não simulam sucesso antes da confirmação do servidor.

Respeitar movimento reduzido, toques rápidos repetidos e pedidos lentos. Skeletons só se há conteúdo estrutural conhecido; mensagens de progresso descrevem a fase real. Evitar barras com percentagens inventadas para geração de IA.

## Estado e decisão

Gosto, adequação nutricional, restrições e FODMAP têm secções e rótulos próprios. Um score não pode apagar um bloqueio. “Dados em falta”, “por rever”, “não elegível”, “proposta” e “aplicado” são estados diferentes, com motivo e próxima ação.

O painel de adaptação apresenta: refeição/data → participantes → problema → operações antes/depois → efeitos conhecidos e informação pendente → editar/aceitar/descartar. Revalidar alterações para todos os presentes e manter histórico de base, variante e composição.

“Fixar” uma decisão não dispensa revalidação. Se o contexto mudar, conservar a escolha visível e pedir resolução do conflito antes de aplicar. Não substituir silenciosamente uma decisão manual.

## Ferramentas académicas e código de produção

Low-fi e PDF do fluxo ficam numa área tracejada de apresentação **só no modo de demonstração**. O PDF abre incorporado, com voltar e descarregar. Estes acessos não devem aparecer como operações familiares normais em produção.

Não migrar o armazenamento local do protótipo como fonte clínica, nem o seu parser/regra de proposta como modelo aprendido. A app usa clientes tipados, evidência e cálculos do backend. Componentes visuais devem funcionar com estados reais de vazio, carregamento, erro, conflito e ausência de capacidade.

## Verificação de cada entrega visual

1440 × 900, 1366 × 768, 768 × 1024 e 390 × 844; claro/escuro/sistema; PT/EN; teclado e foco; zoom a 200%; movimento reduzido. Sem scroll horizontal da página nem ações escondidas por overlays. O mapa pode ter deslocamento próprio e o PDF nativo tem limitações próprias do navegador.

Verificar também famílias sem pessoas, pessoa sem dados físicos, criança, uma pessoa a comer sozinha, convidados, nomes longos, receita sem imagem, composição desconhecida, conexão lenta, erro parcial e concorrência. Usar dados sintéticos separados, sem capturar ou publicar dados pessoais reais.


## Cross-check obrigatório por incremento

Pedido explícito do utilizador em 18 novembro 2026: avançar mantendo comparação contínua com o protótipo. Em cada percurso alterado, confrontar estrutura/densidade, tokens claro/escuro, desktop/mobile, ações e regresso com contexto; registar o que se aproximou e as divergências ainda abertas. Não declarar uma fase concluída apenas por os tokens coincidirem. Evidência e primeiro registo em [cross-check de 18 novembro](crosscheck-prototipo-2026-11-18.md). Capturas com dados pessoais permanecem locais, fora de fixtures públicas.
