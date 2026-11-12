// Shared circular reveal for artwork and workspace surfaces. Cancel the effect
// on completion so long forms are never left clipped or transformed.
export function revealSurface(node:HTMLElement,duration=650,rotate=false){
 const media=matchMedia('(prefers-reduced-motion: reduce)');
 if(media.matches)return ()=>{};
 const radius=Math.hypot(innerWidth,innerHeight)*1.2;
 const centre=Math.max(0,innerHeight*.4-node.getBoundingClientRect().top);
 const animation=node.animate([
  {opacity:0,clipPath:`circle(0px at 50% ${centre}px)`,transform:rotate?'rotate(-9deg) scale(1.12)':'none'},
  {opacity:1,offset:.45},
  {opacity:1,clipPath:`circle(${radius}px at 50% ${centre}px)`,transform:'none'},
 ],{duration,easing:'cubic-bezier(.22,.68,.25,1)',fill:'both'});
 const cancel=()=>animation.cancel();
 const change=()=>{if(media.matches)cancel()};
 media.addEventListener('change',change);
 animation.finished.then(cancel,()=>{}).finally(()=>media.removeEventListener('change',change));
 return cancel;
}
