# ADR-068 — Presenças reutilizáveis e revalidação da agenda manual

Data: 18/10/2026. Estado: implementado e verificado na interface.

## Organização reutilizável

No primeiro passo do percurso é possível copiar a organização da semana anterior:
grupo habitual, tempos, origens e exceções de presenças. As datas das exceções passam
para o mesmo dia da semana de destino, incluindo mudança de mês/ano e horário de verão.
Ausência de organização anterior é explicada; pessoas indisponíveis bloqueiam a cópia
em vez de serem removidas silenciosamente. Respostas antigas não sobrescrevem escolhas
mais recentes ou a organização de outra semana/família.

A semana de destino mantém versão de concorrência e exclusões manuais próprias. Não se
copiam restrições automáticas: são recalculadas para as datas/presentes atuais. Copiar
não guarda refeições nem configuração; o utilizador revê e guarda no passo seguinte.

Cada refeição permite repetir o seu grupo nos sete dias, preservando os outros tempos;
continuam possíveis exceções posteriores. Grupo vazio representa ausência de refeição.
Grupo de uma pessoa continua a usar a agenda individual: não é enviado ao motor partilhado.
Persistência usa o JSON versionado já existente; não é necessária nova migration.

## Revalidação da agenda

O percurso semanal já reavaliava restrições na aceitação e variantes já validavam
participantes/data. A edição manual de uma receita-base passa também a verificar
exclusões automáticas registadas ao criar, trocar receita/presentes ou mudar data/hora/tempo.
Se há conflito, o servidor rejeita com ingredientes e indicação para validar uma variante.
Não substitui automaticamente a receita nem interpreta propostas isoladas como aplicadas.

A rejeição faz rollback das alterações pendentes: data, notas, participantes e porções
anteriores permanecem. Uma restrição de pessoa ausente não bloqueia o prato original.
Notas/local sem mudança de contexto não obrigam a recriar um plano existente.
Regras não registadas, composição de produtos e tolerância clínica continuam limitações.

## Cobertura

Testes API verificam criação rejeitada sem MealEvent/Serving residual, mudança de data,
adição de participante incompatível e original permitido para pessoa não afetada.
Testes web cobrem dias/exceções/DST, isolamento de exclusões e versão, pessoas indisponíveis,
repetição por tempo e instrução de conflito em português. Ver quadro para resultados finais.

## Continuação

T04 ainda inclui padrões nomeados, incerteza e refeições individuais no percurso guiado.
T05 ainda inclui explicação/priorização automática das variantes e escolhas fixadas.
T06 deve ligar produto/rótulo confirmado ao ingrediente efetivo antes de calcular embalagens;
não multiplicar quantidades do ingrediente original pela embalagem de uma alternativa.

Validação: 390 testes API completos passaram antes de acrescentar o caso de mais de
20 presentes; esse caso integra a execução focada final. 123 testes frontend, build,
Ruff e Alembic check passaram. Interface confirmou cópia com exceções e repetição
nos sete jantares; alterações de teste foram descartadas sem guardar.

Execução focada final: 14 testes de agenda/variantes passaram, incluindo grupo com
mais de 20 pessoas e rejeição do ingrediente para o último participante.
