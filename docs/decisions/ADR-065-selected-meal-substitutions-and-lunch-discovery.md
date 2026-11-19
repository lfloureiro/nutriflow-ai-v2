# ADR-065 — Substituições e procura de almoço dentro da refeição selecionada

Estado: implementado localmente, 18/10/2026. Importação de marketplaces depende de acesso externo.

## Problema

O percurso semanal mostrava um catálogo de 57 receitas por baixo da proposta, sem relação
com o prato selecionado. O detalhe só mostrava transformações antigas de uma operação,
não as alterações completas de `FamilyRecipeVariant`. Propostas para ingredientes sem
referência alta FODMAP (ex.: caldo/farinha dos escalopes) não eram apresentadas nesse contexto.

## Decisão

Remover os catálogos globais dos passos de restrições/revisão semanal. O detalhe selecionado
mostra alterações realmente aplicadas pela variante; para a receita base, mostra só as propostas
registadas desse prato, com quantidades/validação pendentes explicitamente indicadas. Não
converte propostas incompletas em ingredientes aplicados ou em adequação confirmada.

A revisão de ingredientes é aberta no próprio detalhe, limitada ao ID da receita base, à
refeição/data e aos presentes. Variantes projetadas resolvem para a sua base por identidade,
sem escolher outra receita por omissão. Trocar de prato desmonta o contexto anterior.

`FamilyWeekSetup.settings.meal_sources` guarda cozinhar/entrega/restaurante por tipo de
refeição, com validação e controlo de versão existentes. O percurso propõe entrega para almoço
e casa para os outros tempos, permitindo alterar. Sem catálogo elegível, almoço de entrega
fica pendente; não é substituído silenciosamente por receita de casa nem dado como guardado.

O detalhe do almoço reúne Uber Eats/Glovo/Bolt Food e restaurantes. Com conta normal,
a opção funcional é abrir a plataforma; não se enviam diagnósticos, participantes ou morada
nesses links. Pesquisa de restaurantes reutiliza o serviço existente, incluindo mapa/lista.
Importação de pratos só fica disponível quando a capacidade local é selecionada, suportada
e live. Resultados importados com composição permitem pedir avaliação semanal para o
slot e fornecedor escolhidos, sem guardar automaticamente. Refeições já guardadas são
preservadas. Importação não foi testada com fornecedores reais por ausência de acesso.

## Acesso externo confirmado

O utilizador confirmou possuir apenas conta normal de cliente. Inspeção local: nenhum
fornecedor de entrega tem credenciais, aprovação consumer ou adaptador registado. A conta
normal não fornece esse contrato. Não se extraíram tokens/cookies nem se criaram credenciais.

Fontes oficiais consultadas em 18/10/2026:
- https://developer.uber.com/docs/consumer-delivery/introduction — acesso antecipado por aprovação.
- https://qcommerce.developer.glovoapp.com/en/documentation/api-partner-api-overview
- https://qcommerce.developer.glovoapp.com/en/documentation/catalog-api-use-cases — gestão de catálogo de parceiros.

## Continuação

T08: escolha de prato externo e evidência de ingredientes no mesmo fluxo; estado pendente
até poder avaliar. T09: obter contrato adequado, implementar adaptador conforme especificações
concedidas e testar observações reais antes de declarar importação live. T04: individuais,
padrões e incerteza continuam pendentes. T07: ampliar rótulos/produtos prioritários.

## Recuperação da pesquisa de restaurantes

A verificação real mostrou timeout de leitura do Overpass: query com prazo de 20 s e
HTTP a desistir aos 8 s. O pedido Overpass passa a ter prazo compatível (25 s mínimo),
com uma segunda instância pública para falhas transitórias. HTTP 4xx, incluindo 429,
não desencadeia rotação. Após falha do Overpass, uma pesquisa Nominatim limitada à
caixa da zona devolve uma seleção de correspondências reais (máximo 40), identificada
como `openstreetmap_nominatim`, com cache curta. Não é um catálogo exaustivo, nem
avaliação nutricional, nem classificação de segurança alimentar.

Verificação direta real: 12 resultados na zona de Lisboa, incluindo identidades OSM e
coordenadas; sem inventar avaliações ou dados nutricionais. Referência técnica:
https://nominatim.org/release-docs/latest/api/Search/ (bounded amenity search).
Instância alternativa publicada: https://wiki.openstreetmap.org/wiki/Overpass_API

Regressão: 386 testes API na execução completa antes da última extensão Nominatim;
14 testes de restaurantes/capacidades na versão final, incluindo essa extensão. Frontend:
112 testes passaram. Build e TypeScript passaram antes da verificação final do rótulo da fonte.

## Verificação final do incremento

- 114 testes frontend, TypeScript e build passaram.
- 386 testes API passaram na regressão completa; depois da extensão Nominatim, os 14
  testes focados de restaurantes/capacidades passaram na versão final. Ruff/diff check passaram.
- Interface: almoço 20/10 → pesquisar Lisboa → 12 restaurantes reais → mapa OpenStreetMap
  carregado → selecionar Tasquinha do Lagarto alterou marcador e estado selecionado da lista.
  Captura `lunch-restaurants-map.png`; não se encomendou nem se aplicou qualquer refeição.
- Mapa incorporado no detalhe, ligado à seleção da lista; sem dados clínicos na URL.
- Sem migration nova. Alterações locais, sem commit/push. Importação consumer continua
  bloqueada por ausência de contrato/acesso e adaptador reais, não apenas por falta de chave.
