# ADR-067 — Evidência de retalho e consolidação da auditoria

Data: 18/10/2026. Estado: implementado na branch v2.

## Decisão

Observações de supermercado podem ter descrição, ingredientes ou ingredientes/nutrição.
A interface distingue as três coberturas; nenhuma é certificação FODMAP por dose.
Tabelas suspeitas inteiramente a zero não preenchem composição de alimentos.
Importação por chave de produto é aditiva/idempotente; não substitui rótulos existentes
ou receitas automaticamente. Alterações futuras de rótulo requerem revisão versionada.

Onze produtos observados com fonte/data, incluindo farinha, amido, cebolinho e iogurte.
Ingredientes associados por catalog_key num índice em memória limitado à família.
Compras são carregadas à abertura do ecrã, com estado acessível; campos e ações têm
nomes explícitos. Estas otimizações não alteram quantidades nem refeições guardadas.

## Auditoria e publicação

A publicação autorizada inclui código, migrações, testes e documentação técnica.
Backups, exportações e capturas pessoais permanecem locais. Auditoria do esquema
inventaria todas as tabelas e oportunidades de índices, sem mudanças especulativas.
Autenticação permanece bloqueio antes de deployment público da API local.

## Verificação

119 testes frontend e 14 workspace/retalho passaram; build, Ruff completo e Alembic
check passaram. Interface confirmou quatro espessantes no ingrediente selecionado,
com nutrição desconhecida da farinha Auchan; reimportação acrescentou zero produtos.
Ver relatórios técnico/esquema e quadro de tarefas para cobertura e pendências.
