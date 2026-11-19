> Referência de continuidade: [estado atual e próximas tarefas](../handoff-2026-11-19.md). Registos intermédios abaixo são históricos; o fluxo atual está em aceitar-trocas-e-refeicao.md.

# Aceitar trocas e confirmar uma refeição

1. Abre **Plano → Semana → refeição → Preparar as trocas**.
2. **Aceitar proposta** regista diretamente a escolha, sem abrir o formulário manual. Também podes ignorar ou escolher **Editar / escolher manualmente**.
3. **Rever receita com estas escolhas** mostra os ingredientes aceites e os valores herdados da base. A edição é opcional; também podes acrescentar outras trocas por preferência.
4. **Seguir para confirmação final** prepara a receita com os mesmos requisitos da original. **Confirmar esta refeição no plano** aplica-a à refeição e atualiza as compras.

## Herança da receita original

Quantidade, unidade (incluindo emb), preparação, rendimento e porções mantêm os dados da original, salvo alteração explícita. Se não havia rendimento ou preparação, continuam ausentes e opcionais; não são inventados. A proposta pode indicar valores próprios, que têm prioridade. Não se convertem embalagens em gramas sem dados de conversão.

Uma alternativa aceite por descrição fica guardada como ingrediente declarado pela família, com a sua descrição e quantidade. Não precisa de nova associação ao catálogo para concluir a edição. Se houver um ingrediente conhecido escolhido, mantém-se esse ID. Descrições não recebem composição nutricional ou rótulo verificado automaticamente.

Confirmar uma edição regista a escolha da família, sem a confundir com uma variante nutricional certificada. O motor rigoroso de variantes mantém os seus requisitos. A gravação no plano continua a verificar conflitos com ingredientes conhecidos e restrições ativas; nutrientes desconhecidos continuam desconhecidos. A base e outras refeições não são reescritas.

## Estado aplicado

Depois de guardar, surge **Confirmada no plano · trocas aplicadas**, incluindo ao recarregar. As propostas da receita base não são reabertas como pendentes nesta refeição. **Alterar esta adaptação** recupera as escolhas aplicadas.

Os campos mantêm-se visíveis enquanto escreves, até fechares o editor. **Guardar para continuar depois** preserva trabalho incompleto. A refeição só muda na confirmação final; se a atualização das compras falhar, a refeição fica guardada e a aplicação indica que é necessário atualizar Compras.
