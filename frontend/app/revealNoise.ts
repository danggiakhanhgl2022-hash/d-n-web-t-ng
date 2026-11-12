import * as THREE from "three";

// Periodic gradient noise, four octaves, like the cached reference. A fixed
// seed keeps comparisons reproducible; the original randomizes its field.
export function createRevealNoise(){
 const size=256,period=8,table=new Uint8Array(512);
 for(let i=0;i<256;i++)table[i]=i;
 let seed=23891;
 const random=()=>{seed=seed*16807%2147483647;return seed/2147483647};
 for(let i=255;i>0;i--){const j=Math.floor(random()*(i+1));[table[i],table[j]]=[table[j],table[i]]}
 for(let i=0;i<256;i++)table[i+256]=table[i];
 const gradients=[[1,1],[-1,1],[1,-1],[-1,-1],[1,0],[-1,0],[0,1],[0,-1]];
 const fade=(t:number)=>t*t*t*(t*(t*6-15)+10);
 const mix=(a:number,b:number,t:number)=>a+(b-a)*t;
 const dot=(hash:number,x:number,y:number)=>{const g=gradients[hash&7];return g[0]*x+g[1]*y};
 const noise=(x:number,y:number,p:number)=>{
  const ix=Math.floor(x),iy=Math.floor(y),fx=x-ix,fy=y-iy;
  const a=ix%p,b=iy%p,c=(ix+1)%p,d=(iy+1)%p;
  return mix(mix(dot(table[table[a]+b],fx,fy),dot(table[table[c]+b],fx-1,fy),fade(fx)),mix(dot(table[table[a]+d],fx,fy-1),dot(table[table[c]+d],fx-1,fy-1),fade(fx)),fade(fy));
 };
 const pixels=new Uint8Array(size*size*4);
 for(let y=0;y<size;y++)for(let x=0;x<size;x++){
  let value=0,weight=.5,scale=1,p=period;
  for(let octave=0;octave<4;octave++){value+=weight*noise(x/size*period*scale,y/size*period*scale,p);weight*=.5;scale*=2;p*=2}
  const n=Math.round(THREE.MathUtils.clamp((value+1)*.5,0,1)*255),offset=(y*size+x)*4;
  pixels[offset]=pixels[offset+1]=pixels[offset+2]=n;pixels[offset+3]=255;
 }
 const texture=new THREE.DataTexture(pixels,size,size,THREE.RGBAFormat);
 texture.wrapS=texture.wrapT=THREE.RepeatWrapping;
 texture.minFilter=texture.magFilter=THREE.LinearFilter;
 texture.needsUpdate=true;
 return texture;
}
