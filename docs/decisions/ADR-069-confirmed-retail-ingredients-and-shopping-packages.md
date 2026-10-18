# ADR-069 — Ingredientes de produto confirmados e embalagens nas compras

Data: 18/10/2026. Estado: implementado e verificado na interface.

## Problema e decisão

Uma observação de retalho pode ser uma proposta para trocar o ingrediente original.
Essa associação não prova que a quantidade do original serve para o produto alternativo.
A escolha de embalagens só aceita o identificador exato de um ingrediente confirmado
que esteja efetivamente na lista de compras.

Rever explicitamente um rótulo utilizável cria um ingrediente próprio da família, com
snapshot nutricional e ligação versionada à observação. O original não é alterado.
A operação é idempotente por família/produto/impressão do rótulo. Ingredientes/nutrição
incompletos ou tabela suspeita inteiramente a zero impedem esta criação. Nutrientes
não publicados mantêm-se desconhecidos; não se tornam zeros nem são copiados de outra marca.

## Percurso

1. Abrir o produto junto ao ingrediente e consultar a fonte; confirmar que se reviu o rótulo.
2. Criar o ingrediente e usar «Atualizar ingredientes» no editor de variantes do mesmo percurso.
3. Identificar o produto e a quantidade/preparação para a receita inteira; validar e aplicar a variante.
4. Atualizar compras. Só o ingrediente efetivo, depois do stock, fica elegível para esse produto.
5. Rever a pré-visualização e confirmar embalagens. Quantidade a comprar, excedente e custo
   estimado ficam guardados separadamente da quantidade necessária do ingrediente.

Converte apenas unidades compatíveis (por exemplo kg↔g, l↔ml), sem densidades ou peso
por unidade inventados. Arredonda o número de embalagens para cima com Decimal.
A estimativa usa o preço observado, sem consulta de stock/preço live, encomenda ou alteração
à despensa. A marcação de comprado conserva a escolha histórica.

## Dados e concorrência

Migration `93c8e18311c4`, filha de `58960d47819f`: tabela
`retail_ingredient_confirmations`, FK na linha de compras, snapshot da escolha e versão.
Confirmações guardam impressões do rótulo e composição, evidência, fonte e data.
Escolher/limpar exige a versão atual do item; bloqueios serializam operações da lista.
Atualizar quantidades/estado e recalcular faltas incrementa a versão relevante.

Mudanças de rótulo/ingrediente ou quantidade deixam a escolha «por rever» e retiram a
contagem/custo ativos. Alterações de stock/plano exigem refrescar faltas antes de confirmar
outra escolha. Receitas/variantes com ingrediente confirmado cuja evidência mudou ficam
bloqueadas para novo uso; refeições e compras históricas são preservadas.

## Limites e continuação

Confirmar rótulo não certifica FODMAP por dose, alergénios ou adequação clínica da família.
A variante continua sujeita à composição e regras registadas. Classificações/tolerâncias
que não estejam registadas não são inferidas de «sem glúten»/«sem lactose».
Só produtos com rótulo utilizável suportam este percurso; falta ampliar esses rótulos,
comparar ofertas entre lojas para o mesmo ingrediente revisto e recolher quantidades
realmente compradas antes de adicionar stock. Fases clínicas continuam em T11.

## Verificação

Migração testada upgrade/downgrade/upgrade na base isolada, e aplicada localmente após
backup. 20 testes API focados e 128 frontend passaram; build passou. Regressão completa
API: 399 passaram antes dos últimos ajustes de catálogo/rollback. Ver quadro de tarefas
para validação final e interface com base sintética própria.

Verificação final: 34 testes API focados passaram após os ajustes de catálogo; 128 frontend,
build/TypeScript, Ruff completo e Alembic check passaram. Na interface isolada, 1 100 g
em falta deram 3 embalagens de 500 g, 400 g de excedente e 5,25 € observados; confirmação
persistiu depois de recarregar. Nenhuma escolha de produto ou receita pessoal foi gravada.
A fixture reproduzível `tests.seed_retail_ui` recusa qualquer DB diferente de
`nutriflow_package_ui`; não usa a base da família nem a de regressão.
