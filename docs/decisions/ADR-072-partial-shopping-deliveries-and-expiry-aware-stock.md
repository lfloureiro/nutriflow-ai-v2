# ADR-072 — Receções parciais, lotes e stock válido para as refeições

Data: 18/10/2026. Estado: implementado; evidência de validação no quadro de tarefas.

## Decisão e percurso

Depois de assinalar «comprado», registar apenas o que chegou agora, em um ou vários
lotes. Cada lote tem quantidade/unidade, local e validade próprios. Se a compra ficar
incompleta, indicar explicitamente o total esperado na unidade do artigo. Não assumir
que a quantidade necessária ou o total de embalagens sugerido corresponde à encomenda.
A próxima entrega acrescenta lotes; concluir a receção mantém o histórico. «Concluir sem
receber mais» fecha o restante pendente sem acrescentar stock.

Separar três valores: stock utilizável no plano, quantidade prevista por receber e
quantidade ainda por comprar. A previsão de entrega nunca conta como stock disponível
para cozinhar. A regeneração desconta o restante confirmado da nova compra para evitar
encomendar duas vezes. Se o plano exigir mais do que stock + entrega pendente, cria uma
nova falta para comprar. Ao concluir uma entrega incompleta, essa previsão deixa de ser
descontada e a lista é recalculada imediatamente. A chegada não está garantida para a
hora da refeição: os valores físicos em falta continuam visíveis; não existe ETA automática.

## API e compatibilidade

POST `/families/{family_id}/shopping-list/items/{item_id}/receipts` recebe `request_id`
(UUID), versão esperada, lista de lotes, `complete`, revisão explícita do rótulo e, na
primeira receção parcial, `expected_quantity`. A unidade desse total é a do artigo.
Até 20 lotes por entrega e 32 entregas por compra; concluir sem mais stock continua
possível após atingir o limite. Uma primeira entrada vazia ou parcial sem total superior
ao recebido é recusada. Unidades incompatíveis e validades sem fuso horário são recusadas.
O total esperado mantém-se fixo; se a encomenda não vier completa, concluir explicitamente.

Bloqueio da lista/artigo e chaves únicas dos lotes protegem a transação. Uma impressão do
pedido normalizado associa UUID à intenção. Repetir o mesmo pedido devolve o resultado
sem recriar stock, mesmo após novas entregas, fecho ou desativação de lotes. Reutilizar o
UUID com dados diferentes ou enviar uma nova intenção com versão antiga causa conflito.
O frontend conserva a identidade da tentativa para repetir um pedido após falha de rede.

O snapshot JSON existente passa a suportar `format_version: 2`, estado parcial/concluído,
quantidade acumulada, total esperado, restante e eventos com os lotes originais. Um novo
pedido acrescenta um evento, sem reescrever os anteriores. A coluna existente conserva
as entradas antigas como concluídas; o endpoint singular anterior continua compatível,
mas os dois protocolos não podem duplicar a mesma compra. Compras com histórico não são
apagadas/desmarcadas. Saldos e validades atuais corrigem-se na despensa, sem alterar a
quantidade originalmente recebida no histórico.

Rótulos alterados bloqueiam novas entradas de stock. Fechar uma entrega sem acrescentar
produtos continua permitido, pois não confirma um novo rótulo nem usa o produto alterado.
Receções e regeneração das compras persistem na mesma transação. Uma nova compra usa
outra chave; histórico e compra pendente do mesmo ingrediente podem coexistir.

## Correção da validade no plano

A auditoria por testes revelou que as compras avaliavam a validade apenas no instante
atual. Um lote válido hoje podia ser descontado de uma refeição posterior à sua validade.
Agora mantêm-se as necessidades por hora/data de refeição e distribui-se um orçamento
local pelos lotes que expiram primeiro (FEFO). Cada quantidade só cobre uma necessidade;
excedentes que expiram antes de outra refeição não cobrem essa refeição.

Isto simula utilização, sem consumir, reservar ou alterar lotes na base de dados. Stock
já expirado no instante de avaliação é sempre excluído. «Utilizáveis no plano» mostra
cobertura elegível e excedentes válidos até à última refeição; a despensa continua a
mostrar os saldos físicos de cada lote. O cálculo inclui os ingredientes efetivos das
variantes e as unidades convertíveis, conservando isolamento familiar.

## Base de dados e limites

Sem migration: reutiliza `shopping_list_items.pantry_receipt` e a unicidade existente dos
lotes. Head `b781e265c904`, 53 tabelas aplicacionais. Histórico limitado por compra, sem
reservas de stock ou tabelas de movimentos neste incremento. Ficam pendentes estornos,
consumo real/sobras, edição explícita do total encomendado e ETA de entregas. O histórico
JSON não substitui um futuro livro de movimentos para cenários de inventário maiores.

## Verificação

Testes integrados: entregas parciais sucessivas, várias validades/locais, conversões,
retries após fecho/desativação, atomicidade de lote inválido, conflitos, isolamento,
rótulo alterado, compatibilidade com entradas antigas, embalagens calculadas após
previsões de entrega e stock que expira antes/entre refeições. Frontend: histórico de
lotes, entrega pendente separada de stock, próxima entrega, fecho e contrato HTTP.


A sessão real tem `autoflush=False`. A verificação no browser detetou que recarregar a
lista antes de gravar explicitamente o novo snapshot podia perder o histórico pendente.
A implementação faz `flush` antes desse recálculo, dentro da mesma transação. Os testes
de receções usam agora essa configuração real, cobrindo persistência e idempotência.

A interface apresenta primeiro compras necessárias, depois entregas pendentes e por fim
o histórico concluído. O teste no browser confirmou 1.000 g recebidos em dois lotes,
500 g pendentes e, após fecho sem mais produtos, a criação imediata de uma compra de
200 g, sem acrescentar stock. Persistência após recarregar verificada na base sintética.

Validação final: 438 testes API completos, 17 focados com configuração de produção e
147 frontend passaram. TypeScript/build, Ruff e Alembic check sem erros.
