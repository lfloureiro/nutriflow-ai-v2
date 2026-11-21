# NutriFlow — receitas, imagens e duplicados (21/11/2026)

## Fonte e cobertura real

A lista de receitas entregue pelo utilizador é o PDF `NutriFlow AI.pdf`, páginas 2–19 (exportação 21/11/2026 19:04). O documento tem **69 entradas, 68 designações distintas**. «Frango rápido · família» surge em duplicado (página 11). **Um nome duplicado não prova que ingredientes, porções ou vínculos são iguais**; verificar os dados antes de consolidar.

A correspondência de ilustrações existente no código `apps/web/src/mealHeroImages.ts` cobre **20 das 69 entradas** da lista, por 18 ficheiros WebP (várias receitas familiares partilham a imagem-base). Uma destas imagens, `bifanas-com-natas.webp`, já está efetivamente no Git. As restantes **17 são ficheiros binários externos** presentes no pacote `nutriflow-receitas-imagens-v2.1.21.zip`, produzido nesta conversa e com manifesto SHA-256. O ZIP **não** está comitado e necessita de ser extraído no computador local (script `INSTALAR-IMAGENS.ps1` incluído). O instalador **não substitui** a imagem das bifanas já comitada.

As 49 entradas restantes do PDF **não têm ainda imagens próprias geradas nesta fase**. Por política visual, não associar uma imagem de outro prato pelo tipo de refeição ou semelhança vaga. Elas mantêm fotografia previamente aprovada do catálogo quando houver, ou fallback neutro.

## Intake de receitas novas e receitas adaptadas

Implementação:
- `apps/api/app/services/recipe_image_generation.py`: geração opcional de foto ilustrativa via API de imagens OpenAI, após o registo da receita; não bloqueia a gravação. Só envia nome e ingredientes, nunca perfis, restrições ou dados de saúde.
- `apps/api/app/api/routes/recipes.py`: ao criar ou alterar nome/ingredientes, agenda a geração com FastAPI `BackgroundTasks`.
- `apps/api/app/api/routes/recipe_variants.py`: adaptações aprovadas também usam o mesmo processo, inclusive quando é reutilizada uma receita.
- As imagens são guardadas em `data/recipe-images` (ou `NUTRIFLOW_RECIPE_IMAGE_DIRECTORY`) e expostas através de endpoint limitado à família. São identificadas pela identidade da receita e composição; a fotografia antiga não passa por atual depois de alterar ingredientes.
- `RecipeRead.image_url` só é preenchido quando o ficheiro existe, e a vista Receitas reutiliza a imagem gerada com rótulo de **ilustração IA**. A imagem pode aparecer apenas após o pedido de geração terminar e a listagem ser atualizada.
- Requisitos: `OPENAI_API_KEY` válida, acesso externo e `NUTRIFLOW_RECIPE_IMAGE_GENERATION_ENABLED=true`. Em ausência da chave, a receita continua a ser guardada mas **não há geração automática**. O uso da API pode ter custos. Configurar armazenamento persistente antes de produção.

## Duplicados familiares

Diagnóstico do código anterior: `create_recipe_edit` usava sempre `recipe-edit:<UUID>` e criava novas linhas `Recipe` e `FoodItem` em cada submissão, mesmo quando as alterações já existiam.

A correção introduzida em `apps/api/app/services/recipe_edit.py`:
1. Bloqueio transacional da receita base (proteção contra dois pedidos concorrentes).
2. Compara o mesmo `base_recipe_id`, porções, substituições (ID do ingrediente ou nome normalizado), quantidades, unidades, preparação e ordem.
3. Reutiliza a **receita familiar ativa, íntegra e equivalente**, sem novas receitas nem ingredientes. Alterações materiais criam receitas distintas; títulos diferentes não forçam duplicação.
4. Preserva as variantes pré-existentes e o histórico sem apagar nenhum registo.

Para procurar duplicados passados, chamar `GET /api/families/{family_id}/recipe-variants/duplicates` na API. Responde com grupos de receitas familiares com composição comprovadamente idêntica e IDs dos registos, com ação `manual_review_required`. **Não fundir automaticamente**: verificar refeições que usam os IDs, variantes inativas e histórico.

## Testes, limitações e passos seguintes

- Testes de deduplicação: mesma operação repetida retorna mesmo ID, inclusive descrição de ingredientes por nome, e alteração real de quantidade cria nova receita.
- Teste de auditoria: simula dois registos familiares iguais no caminho antigo e verifica inventário sem apagar histórico.
- Testes de imagem: identidade por receita, invalidação quando os ingredientes mudam, ausência de chamada externa sem chave e presença de URL só depois da imagem existir.
- Validar no CI API/Web/UX E2E e, no Chrome, um pequeno-almoço, uma receita importada, bifanas e uma nova receita com geração ativada.
- **Sem executar a API contra a base de dados real do utilizador não é possível determinar se as duas entradas de «Frango rápido · família» têm a mesma composição**. O endpoint de auditoria permite essa verificação sem risco.
- O plano de trabalho seguinte é produzir imagens para as 49 entradas ainda sem cobertura, em lotes, guardando origem e hash para cada fotografia.
