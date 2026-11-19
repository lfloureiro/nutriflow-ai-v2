# ADR-064 — Presenças por refeição no percurso semanal

Estado: implementado parcialmente no v2 local, 18/10/2026.

## Decisão

`FamilyWeekSetup.settings.attendance` guarda exceções ao grupo habitual por data e tipo de
refeição. Campo omitido significa grupo habitual; lista vazia de presentes significa que
não se gera uma refeição. O JSON existente mantém o controlo de versão otimista; nenhuma
migração é necessária. Registos antigos sem o campo continuam legíveis.

Cada slot da proposta pode enviar `person_ids`. A API verifica duplicados, subconjunto do
grupo e pertença familiar, incluindo membros do grupo sem slots. Não permite sobreposição
da mesma pessoa na mesma data/tipo de refeição. Ausência de `person_ids` mantém o contrato
anterior de grupo comum. Dois ou mais participantes continuam obrigatórios num slot gerado.

O motor exige grupo consistente entre candidatos de um slot, mas admite grupos distintos
entre slots. Avalia os limites de cada pessoa só nos slots frequentados. Durante a pesquisa
parcial, pessoas sem refeições nessa combinação ainda não entram na avaliação. A aceitação
usa o pedido com as mesmas presenças e recalcula evidência nutricional e restrições atuais.

A pré-visualização das restrições semanais também recebe exceções de presenças. Exclusões
manuais continuam a valer para toda a semana; exclusões automáticas são calculadas no
servidor para os presentes em cada slot. Compras usam as porções realmente materializadas.

## Limites e próximos passos

O quadro aceita refeições sem presentes e grupos com pelo menos duas pessoas. Mostra aviso
para um participante e impede avançar; refeições individuais continuam disponíveis na agenda.
Padrões reutilizáveis, presença incerta, vários grupos/localizações na interface e edição
conjunta de refeições já planeadas permanecem trabalho futuro de T04/T05.

## Verificação

Testes de API cobrem persistência, validação das exceções, grupos alternados, limite semanal
de um ausente e restrições SIBO por presentes, incluindo aceitação e pessoas materializadas.
Frontend cobre transporte de presenças até à aceitação. Verificação no browser em
`../audits/2026-10-18/meal-attendance-interface-verification.md`.
