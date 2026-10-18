# ADR-066 — Alternativas visíveis e semanas guardadas no início

Estado: implementado localmente no v2, 18/10/2026.

## Problema

A agenda guardada mostrava apenas o nome da receita e as porções. Propostas de troca
não apareciam nos cartões; a revisão de ingredientes colocava a alternativa noutra secção.
Nas compras era preciso abrir detalhes, muitas vezes sem produto de loja associado.
O início encaminhava sobretudo para gerar uma nova semana, dificultando consultar a agenda.

## Decisão

- Início: bloco «As nossas semanas», com navegação anterior/seguinte, esta/próxima semana,
  escolha de data e refeições efetivamente guardadas. Cada cartão inclui alterações aplicadas
  ou propostas da sua própria receita. Abre a semana correspondente na agenda.
- Menu Plano abre a agenda semanal; gerar propostas continua num botão explícito.
- Separar data consultada de hoje: navegar numa semana não muda a referência de «Hoje»
  nem a semana usada para «planear próxima semana».
- Ingrediente e alternativa na mesma linha, com seta e estado. Usado nos ingredientes da
  receita, necessidades do plano e itens de compras. Não assume equivalência de quantidades.
- Cartões da semana/dia incluem as trocas. Detalhe da agenda reutiliza a revisão limitada
  ao prato/data/presentes, tal como o percurso guiado. «Ver agenda» preserva a semana escolhida.
- Variantes e transformações realmente aplicadas têm prioridade sobre propostas. Propostas
  rejeitadas são omitidas; propostas ainda não aplicadas não alteram receitas nem compras.
- As alternativas nas compras são obtidas só das receitas presentes no intervalo guardado
  da lista. Pedidos por intervalos de até 14 dias respeitam o contrato existente da API.
- Sem migration nem alteração de dados alimentares nesta entrega. Labels não certificam
  adequação clínica; são propostas registadas e alterações efetivamente guardadas.

## Desenvolvimento e verificação

Vite usa polling de ficheiros no Windows: a observação nativa não estava a invalidar os
módulos após alterações por ferramentas, deixando o browser numa versão anterior. Reinício
local efetuado, com confirmação de que os módulos atualizados chegam à interface.

Testes de apresentação/identidade/estado, navegação por semanas e datas de fronteira;
verificação real de início → próxima semana → agenda e alternativas na linha das compras.

Verificação concluída: 118 testes frontend, TypeScript/build e diff check passaram.
Regresso entre menus repõe o topo da página e preserva a semana aberta. Navegação e
consulta na interface foram de leitura; dados de refeições e compras não foram alterados.
