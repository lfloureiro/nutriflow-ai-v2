# ADR-070 — Entrada efetiva das compras na despensa

Data: 18/10/2026. Estado: implementado; validação descrita no quadro de tarefas.

## Decisão

Separar assinalar «comprado» de confirmar o que chegou a casa. No cartão comprado,
introduzir quantidade total recebida, unidade, local e validade opcional, e confirmar
explicitamente ingrediente/rótulo/quantidade. Não copiar automaticamente a necessidade
da receita nem o total previsto de embalagens: podem diferir da compra real.

POST `/families/{family_id}/shopping-list/items/{item_id}/receipt` exige versão atual,
artigo comprado com ingrediente visível/ativo e unidade fisicamente compatível. Não
estimar densidade ou peso de unidades. Produtos confirmados cujo rótulo/composição
mudou exigem revisão antes da entrada. Artigos livres sem ingrediente são registados
manualmente na despensa; não se adivinha a correspondência.

A regeneração adquire o bloqueio da lista antes de calcular necessidades, serializando
a leitura com entradas de compras concorrentes. Uma transação bloqueia lista e artigo, cria o lote e guarda no artigo um snapshot JSON
imutável `pantry_receipt`: quantidade/unidade/local/validade recebidos, instante, ID do
lote e escolha de produto histórica. A chave única do lote deriva do artigo. Repetir
exatamente a confirmação devolve o registo existente, mesmo com a versão antiga;
quantidades/dados diferentes devolvem conflito e exigem corrigir o lote na despensa.
Desativar ou consumir o lote nunca permite que uma repetição recrie stock.

Compras recebidas preservam o histórico: não podem ser apagadas, desmarcadas ou ter
quantidade alterada. O cartão mostra a entrada; correções atuais fazem-se no lote.
O snapshot não pretende refletir o saldo atual do lote. A chave do artigo recebido muda
para `received:{id}`; a regeneração ignora-o ao procurar artigos pendentes e pode criar
uma compra futura do mesmo ingrediente, sem duplicar o histórico.

## Base de dados e limites

Migration `b781e265c904`, após `93c8e18311c4`, acrescenta apenas JSON nullable a
`shopping_list_items`; conserva as 53 tabelas aplicacionais. Reutiliza a unicidade
(família, stock_key) existente nos lotes e bloqueio transacional de compras.
O ID do lote no snapshot é referência histórica, sem nova relação de ciclo de vida;
os endpoints de despensa desativam lotes e não apagam o histórico da compra.
Backup privado anterior à migration, excluído do Git. Nenhuma entrada criada na família
real pelo agente; teste de interface numa base isolada com família sintética.

Entrada de uma compra corresponde a um lote. Compras com várias validades devem ser
registadas como lotes separados na despensa; divisão/receções parciais e estornos com
movimentos de inventário ficam para uma fase posterior. A confirmação não certifica
adequação clínica nem efetua encomendas/pagamentos.

## Verificação

Testes integrados cobrem quantidade efetiva (1.500 g recebidos para 1.100 g em falta),
abate imediato das necessidades, idempotência, conflito de versão, unidades incompatíveis,
isolamento familiar, rótulo alterado, confirmação explícita e histórico após desativação.
A regeneração após esgotar stock mantém o recebido e cria nova compra pendente.
Frontend testa formulário condicionado à compra, quantidade inicialmente vazia,
confirmação obrigatória, snapshot sem novo formulário e contrato HTTP.
Browser: comprar → confirmar 1.500 g → stock 1.600 g → falta zero → recarregar.


Regressão completa: 407 testes API e 132 frontend passaram; TypeScript/build, Ruff e
Alembic check sem erros. A primeira execução tinha quatro erros de permissões na pasta
temporária do Windows; a repetição completa usou pasta própria do projeto e passou.

Verificação final: 13 testes focados após o ajuste de bloqueio da regeneração passaram.
Downgrade/upgrade da nova migration e Alembic check passaram na base isolada.
