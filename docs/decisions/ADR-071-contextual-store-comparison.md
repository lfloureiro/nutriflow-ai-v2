# ADR-071 — Comparação de lojas no contexto do ingrediente

Data: 18/10/2026. Estado: implementado; validação no quadro de tarefas.

## Problema

As observações comerciais tinham preços de embalagens diferentes sem preço normalizado.
Além disso, depois de uma variante passar a usar um ingrediente confirmado, a ligação
exata ao produto ocultava outras lojas do mesmo grupo de descoberta. Listar todos os
rótulos em cartões abertos prolongava desnecessariamente o detalhe da refeição.

## Decisão

O GET de alternativas acrescenta `price_comparison` calculado a partir de preço e
quantidade observados. Com Decimal, converter apenas massa (mg/g/kg) para €/kg e
volume (ml/l) para €/l. Sem densidades ou pesos presumidos de unidades. Preços ou
embalagens desconhecidos/inválidos devolvem valor nulo e motivo, nunca zero presumido.
A moeda é EUR, correspondente às observações portuguesas existentes.

A interface agrupa por grupo comercial **e** unidade de referência, ordena pelo preço
observado normalizado e mantém preço de embalagem, loja, URL, data e cobertura do rótulo.
Não mistura categorias nem massa/volume numa ordenação de preço. Sem recomendação clínica,
sem declaração de equivalência de composição e sem cálculo de quantidades da receita
original para outro produto. Promoções, entrega e disponibilidade não são garantidas.
Comparação usa as onze observações existentes; esta fase não representa nova consulta live.

Descoberta de produtos relacionados expande apenas os grupos já ligados ao ingrediente
em revisão. Não altera `applicable_food_item_ids`, a identidade do ingrediente ou a
validação exata exigida para escolher embalagens nas compras. Quando existe uma escolha
histórica cujo rótulo mudou, o URL dessa escolha pode conservar o contexto de descoberta;
continua a não ser uma confirmação nem permissão para usar o ingrediente desatualizado.

## Percurso e integração

- Compras: «Comparar lojas e rever rótulos» no artigo pendente, junto à escolha efetiva.
- Revisão alimentar e detalhe de receitas: mesma comparação com grupos relevantes.
- Vários produtos: tabela e «Rever rótulo»; apenas o detalhe selecionado fica aberto.
- Um só produto: cartão direto, com preço unitário quando calculável.
- Informação incompleta permanece explícita e impede criar ingrediente utilizável.
- Confirmar rótulo continua separado de validar/aplicar variante e de comprar/receber.
- A confirmação da revisão do rótulo fica associada à impressão da evidência; um rótulo
  alterado exige nova marcação, conservando a revisão de composição independente do preço.

Tabelas têm caption, cabeçalhos de coluna/linha e região horizontal focável para ecrãs
estreitos. A seleção tem estado acessível e destaque visual. Nada é comprado ou alterado
nas receitas quando se abre um rótulo.

## Base de dados, desempenho e limites

Sem migration, nova tabela ou índice. O preço normalizado é derivado para evitar valores
persistidos desatualizados. Mantêm-se 53 tabelas aplicacionais e head `b781e265c904`.
Sem pedidos HTTP adicionais por linha: reutiliza a consulta de alternativas já existente.
A comparação não substitui a futura revisão de mais rótulos e observações recentes, nem
agregação do cesto por loja, custos de entrega, disponibilidade live ou integração comercial.

## Verificação

Testes API de conversões, preço desconhecido, unidades sem peso, números inválidos,
preços de embalagens diferentes, preservação de evidência e isolamento das confirmações
privadas. Frontend verifica contexto do ingrediente confirmado, grupos/unidades separados,
ordenação e falta de preço, único rótulo aberto e ausência de aplicação automática.
Browser em base sintética: compras de reposição → tabela Auchan/Continente → abrir rótulo
incompleto → abrir rótulo confirmado; só o último detalhe permanece visível.
A família real não foi alterada. Capturas e dados de teste ficam fora da publicação.

Regressão: 421 testes API completos, 36 focados e 140 frontend passaram. TypeScript/build,
Ruff e Alembic check sem erros. Sem alteração de dados da família real.
