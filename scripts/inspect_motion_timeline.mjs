import fs from 'node:fs';
import path from 'node:path';
import {objectAt} from '../frontend/app/sceneTimeline.ts';
const dir=path.resolve('frontend/public');
const scenes=JSON.parse(fs.readFileSync(path.join(dir,'renaissance/3d/scenes.json'),'utf8'));
for(const scene of scenes.filter(s=>['sidekick','agentic','online','retail'].includes(s.id))){
 const state=JSON.parse(fs.readFileSync(path.join(dir,scene.timeline),'utf8'));
 console.log('\n'+scene.id);
 for(const t of [0,1,2,3,4,5,7,10]){
  const entries=[];
  for(let i=0;i<scene.assets.length;i++){
   const v=objectAt(state,`asset-${i+1}`,t);
   entries.push({timeline:v.timeline,animations:v.animations});
  }
  console.log(t,JSON.stringify(entries));
 }
}
