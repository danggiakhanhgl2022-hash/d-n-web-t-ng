"use client";
import {useEffect,useRef} from "react";
import {revealSurface} from "./revealMotion";
export default function WorkspaceTransition({transitionKey}:{transitionKey:string}){
 const curtain=useRef<HTMLDivElement>(null);
 useEffect(()=>{
  if(matchMedia('(prefers-reduced-motion: reduce)').matches)return;
  const overlay=curtain.current;
  const cover=overlay?.animate([{opacity:.7},{opacity:0}],{duration:500,easing:'ease-out',fill:'both'});
  const workspace=document.querySelector('.workspace');
  const reveal=workspace instanceof HTMLElement?revealSurface(workspace,720):undefined;
  const art=document.querySelector('.renaissance-backdrop');
  const artwork=art instanceof HTMLElement?revealSurface(art,900,true):undefined;
  return()=>{cover?.cancel();reveal?.();artwork?.()};
 },[transitionKey]);
 return <div className="workspace-transition" ref={curtain} data-transition-key={transitionKey} aria-hidden="true"/>;
}
