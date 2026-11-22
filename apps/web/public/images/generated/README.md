# NutriFlow — receitas com imagens geradas por IA

Versão: **2.1.19**. Fotografia ilustrativa, **não é um registo de prato efetivamente preparado**.

As imagens são correspondidas pelo título normalizado exato em `mealHeroImages.ts`. Uma imagem definida diretamente na API/receita tem sempre prioridade.

O pacote local de imagens contém sete ficheiros `webp`:
- `bifanas-com-natas.webp`
- `escalopes-madeira.webp`
- `frango-rapido.webp`
- `salmao-ervas.webp`
- `torrada-mista.webp`
- `aveia-iogurte-banana.webp`
- `banana-frutos-secos.webp`

**Instalação local:** descarregar o pacote `nutriflow-imagens-v2.1.19.zip` entregue no chat, extrair e executar `INSTALAR-IMAGENS.ps1 -Repo D:\Python\nutriflow-ai-v2`. Os ficheiros WebP são copiados para esta pasta. Os ficheiros não foram carregados nesta branch por a integração GitHub atual não aceitar binários. Um erro de carregamento usa a imagem externa conhecida da receita, ou o fallback neutro. O utilizador pode adicionar os WebP ao Git local posteriormente; confirmar os hashes com `manifest.json` do ZIP.

**Proveniência:** ilustrações produzidas por IA, não fotos reais e não garantia da composição exata da receita. Nunca as tratar como evidência nutricional. O histórico de consumo simulado é apenas uma pré-visualização do frontend; não é gravado em tabelas de consumo.

## Atualização v2.1.20 — bifanas incluídas no Git

`bifanas-com-natas.webp` está agora **comitado** em `apps/web/public/images/generated/` (320 × 240, 4962 bytes; SHA-256 `38650895acfac74dbaaeb0546a868a06b44705c47d3b60d3831cb892f88b41ca`). Usado automaticamente por `resolveMealHeroImage` para «Bifanas com natas», no hero e no cartão do jantar; o teste de integridade em `mealHeroImages.test.ts` confirma a presença e o conteúdo binário. O pacote externo continua opcional para as outras seis fotografias. A fotografia é uma ilustração por IA, não o prato efetivamente preparado.

## Lote de imagens v2.1.21 (21-11-2026)

O ZIP entregue `nutriflow-receitas-imagens-v2.1.21(1).zip` contém 18 WebP
em `apps/web/public/images/generated/`, `manifest.json` com SHA-256 e
`INSTALAR-IMAGENS.ps1`. O mapa de títulos normalizados em
`apps/web/src/mealHeroImages.ts` já referencia estes ficheiros.

**Importante:** entregar o ZIP no chat não publica os seus ficheiros binários
no repositório. A branch de desenvolvimento só contém a miniatura das bifanas
até à instalação e ao commit dos restantes WebP. Não afirmar cobertura real
de imagens enquanto o Git não contiver os assets.

Para instalar localmente, extrair o ZIP e executar a partir da pasta extraída:

```powershell
.\INSTALAR-IMAGENS.ps1 -Repo D:\Python\nutriflow-ai-v2
cd D:\Python\nutriflow-ai-v2
git branch --show-current
git status --short
git add apps/web/public/images/generated/*.webp
git commit -m "assets(recipes): publish v2.1.21 illustrated meal pack"
git push origin HEAD:codex/ux-drawer-next-batch-20261119
```

Antes do commit confirmar que a branch ativa é a de desenvolvimento e
que os ficheiros não substituem alterações locais inesperadas. O script
verifica o SHA-256 de cada imagem e preserva a imagem das bifanas já existente.

O backend dispõe de geração automática para receitas novas/alteradas, mas
depende de `OPENAI_API_KEY` e de
`NUTRIFLOW_RECIPE_IMAGE_GENERATION_ENABLED=true`. São imagens ilustrativas,
não comprovativos de ingestão.
