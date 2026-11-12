export type Keyframe={position:number;value:number;handles?:number[];connectedRight?:boolean;type?:string};
export type SceneState={sheetsById:Record<string,{staticOverrides?:{byObject:Record<string,Record<string,unknown>>};sequence:{length:number;tracksByObject:Record<string,{trackData:Record<string,{keyframes:Keyframe[]}>;trackIdByPropPath:Record<string,string>}>}}>};
const bezier=(t:number,a:number,b:number)=>3*(1-t)*(1-t)*t*a+3*(1-t)*t*t*b+t*t*t;
export function sample(keys:Keyframe[],time:number):number|undefined{
 if(!keys.length)return;
 if(time<=keys[0].position)return keys[0].value;
 const last=keys[keys.length-1];if(time>=last.position)return last.value;
 let right=1;while(keys[right].position<time)right++;
 const a=keys[right-1],b=keys[right];if(a.connectedRight===false)return a.value;
 let t=(time-a.position)/(b.position-a.position);
 if(a.type==="bezier"&&a.handles&&b.handles){
  const x=t;let lo=0,hi=1;
  for(let i=0;i<18;i++){t=(lo+hi)/2;if(bezier(t,a.handles[2],b.handles[0])<x)lo=t;else hi=t}
  t=bezier(t,a.handles[3],b.handles[1]);
 }
 return a.value+(b.value-a.value)*t;
}
const compiled=new WeakMap<SceneState,Map<string,{base:Record<string,unknown>;tracks:{path:string[];keys:Keyframe[]}[]}>>();
export function objectAt(state:SceneState,key:string,time:number):Record<string,unknown>{
 const sheet=state.sheetsById.Scene||Object.values(state.sheetsById)[0];
 let cache=compiled.get(state);if(!cache){cache=new Map();compiled.set(state,cache)}
 let entry=cache.get(key);if(!entry){const tracks=sheet.sequence.tracksByObject[key];entry={base:sheet.staticOverrides?.byObject[key]||{},tracks:tracks?Object.entries(tracks.trackIdByPropPath).map(([path,id])=>({path:JSON.parse(path),keys:tracks.trackData[id].keyframes})):[]};cache.set(key,entry)}
 // Copy only branches touched by a track; never mutate shared source overrides.
 const value={...entry.base};const copied=new Set<string>();
 for(const {path,keys} of entry.tracks){
  const result=sample(keys,time);if(result===undefined)continue;
  let target=value,prefix='';
  for(const part of path.slice(0,-1)){prefix+='/' + part;if(!copied.has(prefix)){target[part]={...(typeof target[part]==='object'&&target[part]?target[part] as Record<string,unknown>:{})};copied.add(prefix)}target=target[part] as Record<string,unknown>}
  target[path[path.length-1]]=result;
 }
 return value;
}
