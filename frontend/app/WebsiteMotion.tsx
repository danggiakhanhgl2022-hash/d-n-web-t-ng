"use client";
import {useEffect} from "react";
import {revealSurface} from "./revealMotion";

export default function WebsiteMotion(){
 useEffect(()=>{
  const media=matchMedia('(prefers-reduced-motion: reduce)');
  const seen=new WeakSet<Element>(),running=new Set<()=>void>();
  const observer=new IntersectionObserver(entries=>{
   for(const entry of entries){
    if(!entry.isIntersecting)continue;
    const node=entry.target as HTMLElement;observer.unobserve(node);
    if(media.matches||node.contains(document.activeElement))continue;
    node.dataset.revealed='true';
    const stop=revealSurface(node,node.matches('.chapter-stage')?850:480);
    running.add(stop);
    // Artwork rotates on its own layer; inputs and text stay upright.
    if(node.matches('.chapter-stage'))node.dataset.artArrival='true';
    window.setTimeout(()=>running.delete(stop),1000);
   }
  },{threshold:.08});
  const scan=()=>{
   document.querySelectorAll<HTMLElement>('.app-shell .chapter-stage,.app-shell .panel,.app-shell .stat-card,.app-shell .export-card,.app-shell .modal').forEach(node=>{
    if(seen.has(node))return;seen.add(node);observer.observe(node);
   });
  };
  scan();const mutations=new MutationObserver(scan);
  mutations.observe(document.body,{childList:true,subtree:true});
  return()=>{mutations.disconnect();observer.disconnect();for(const stop of running)stop()};
 },[]);
 return null;
}
