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
