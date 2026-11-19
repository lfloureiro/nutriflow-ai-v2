import {useEffect,useRef} from "react";
import {registerNavigationBlocker} from "./navigation";
export function useUnsavedChanges(value:unknown,message:string){
 const encoded=JSON.stringify(value);const baseline=useRef(encoded);const current=useRef(encoded);current.current=encoded;const prompt=useRef(message);prompt.current=message;
 const isDirty=()=>baseline.current!==current.current;
 const confirmDiscard=()=>!isDirty()||window.confirm(prompt.current);
 useEffect(()=>{const release=registerNavigationBlocker(confirmDiscard);const unload=(event:BeforeUnloadEvent)=>{if(isDirty()){event.preventDefault();event.returnValue="";}};window.addEventListener("beforeunload",unload);return()=>{release();window.removeEventListener("beforeunload",unload);};},[]);
 return {dirty:isDirty(),confirmDiscard,markSaved:()=>{baseline.current=current.current;}};
}
