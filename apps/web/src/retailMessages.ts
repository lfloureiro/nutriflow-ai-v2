export function retailActionError(error:unknown,pt:boolean):string {
 const message=error instanceof Error?error.message:String(error);
 if(!pt)return message;
 if(message.includes("Refresh shopping"))return "Atualiza a lista a partir do plano para usar as quantidades atuais dos ingredientes efetivos.";
 if(message.includes("Shopping item changed"))return "Este item mudou. Recarrega as compras antes de escolher o produto.";
 if(message.includes("Product label changed"))return "O rótulo mudou. Recarrega os produtos e revê o rótulo antes de confirmar.";
 if(message.includes("exact confirmed ingredient"))return "Este produto tem de corresponder ao ingrediente efetivo. Aplica primeiro uma variante validada.";
 if(message.includes("Complete usable"))return "Falta um rótulo com ingredientes e informação nutricional utilizável.";
 if(message.includes("units are incompatible"))return "As unidades não são compatíveis. Confirma o peso ou volume; não foi assumida uma densidade ou dimensão da unidade.";
 return message;
}
