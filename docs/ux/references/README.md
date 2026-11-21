# NutriFlow AI v2 — referências visuais aprovadas (21/11/2026)

**Decisão do utilizador:** os cinco protótipos gerados para Início, Receitas, Família, Compras e Despensa são o **alvo visual final**, não meras sugestões. A Semana v2.0.86 permanece o ecrã já aprovado e a base visual do shell comum.

O manifesto `manifest.json` fixa o nome, o SHA-256 e a dimensão de referência dos cinco PNG (1672 × 941 px). A cópia integral dos PNG está preservada na Biblioteca do utilizador em **NutriFlow AI v2 / UX References** e no pacote de entrega `nutriflow_ux_references_v1.zip` criado neste chat.

## Instalação dos PNG no checkout do repositório

O conector de escrita GitHub disponível neste contexto só permite criar texto UTF-8 diretamente. Assim, os **binários PNG ainda não estão comitados na branch**. Não substituir nem converter as cinco referências para SVG genérico ou imagens semelhantes. Para os guardar também na árvore Git, extrair o ZIP (estrutura já inclui `docs/ux/references/*.png`) na raiz do checkout e fazer um commit dedicado após validação dos hashes. Não declarar os PNG no Git sem verificar a sua presença.

## Critérios de aceitação

1. Reproduzir a mesma ordem, estrutura, proporção e hierarquia de conteúdo demonstrada no respetivo PNG, preservando todos os fluxos reais, dados, regras nutricionais, drawers e estados de erro.
2. **Prioridade à vista integral:** o conteúdo essencial da página principal deve caber no viewport de desktop sem scroll vertical quando a altura o permitir; listas longas, dados e formulários reais podem exigir scroll próprio e nunca devem ser truncados para falsificar o resultado.
3. Shell único em todas as rotas, mesmo tema e tipografia, brilho âmbar controlado, sombras e gradientes da referência. Não reintroduzir diferenças `.app-shell--meals` na sidebar.
4. Capturar screenshots sintéticos e comparar por ecrã com os PNG em **dark**; reproduzir os mesmos tokens em light, sem copiar cores de fundo escuro literalmente.
5. Cada captura de referência contém **dados ilustrativos**, não se devem inventar membros, números nutricionais, estimativas ou ingredientes para a aplicação real. Mostrar estados vazios legítimos.
6. Implementação progressiva: Início → Receitas → Família → Compras → Despensa. Só avançar da validação visual de cada ecrã após verificar composição, interação e integridade de conteúdo; regressão do shell e da Semana no CI.
7. PR #76 em draft; não alterar base de dados real, serviços locais ou `main`.

## Pendentes do lote

- O Início já começou a usar a fotografia da próxima refeição planeada (mesmo resolvedor seguro da Semana), mantendo fallback quando a fotografia não está validada.
- Layout do Início mais compacto a larguras desktop; falta verificar com o utilizador em 100% de zoom e comparar screenshot real com a referência, incluindo famílias com muitos membros.
- Receitas, Família, Compras e Despensa requerem revisão específica da composição dos PNG além do passe comum de v2.0.87.
- Os cinco PNG têm de ser integrados como binários no Git para que o conjunto seja completamente autocontido; as cópias persistentes na Biblioteca e o pacote ZIP já estão disponíveis.

