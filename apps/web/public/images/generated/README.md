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
