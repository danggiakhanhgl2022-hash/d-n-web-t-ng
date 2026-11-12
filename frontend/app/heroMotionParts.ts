import * as THREE from 'three';
import {clone} from 'three/addons/utils/SkeletonUtils.js';

// Keep the original skeleton and geometry intact. Partition animation tracks,
// not vertices: a skinned mesh can depend on bones from several branches.
export type MotionPart={name:string;clip:THREE.AnimationClip};

function partFor(node:THREE.Object3D,root:THREE.Object3D):string{
 const path:string[]=[];
 for(let current:THREE.Object3D|null=node;current&&current!==root;current=current.parent)path.push(current.name.toLowerCase().replace(/[^a-z0-9]/g,''));
 const has=(term:string)=>path.some(name=>name.includes(term));
 const person=has('robedwomanrig')?'woman':has('robedmanrig')?'man':'shared';
 if(person==='woman'){
  if(has('skateboard')||has('skatedeck'))return 'woman.skateboard';
  if(has('coffeecup'))return 'woman.cup';
  if(has('handrwoman'))return 'woman.right-hand';
  if(has('handlwoman'))return 'woman.left-hand';
  if(has('shoelacesl'))return 'woman.left-shoelace';
  if(has('shelacesr'))return 'woman.right-shoelace';
  if(has('womanhead'))return 'woman.head';
  return 'woman.body-and-rig';
 }
 if(person==='man'){
  if(has('bagarmature2')||has('pinkbag001'))return 'man.bag-2';
  if(has('bagarmature')||has('pinkbag'))return 'man.bag-1';
  if(has('handrman'))return 'man.right-hand';
  if(has('handlman'))return 'man.left-hand';
  if(has('manhead'))return 'man.head';
  return 'man.body-and-rig';
 }
 return person;
}

export function splitHeroClip(root:THREE.Object3D,clip:THREE.AnimationClip):{parts:MotionPart[];unresolved:string[]}{
 return splitClip(root,clip,node=>partFor(node,root));
}

// For the later GLBs, retain named object branches (book armatures, POS
// components and animated props). Bone tracks stay with their owning branch.
export function splitObjectClip(root:THREE.Object3D,clip:THREE.AnimationClip):{parts:MotionPart[];unresolved:string[]}{
 return splitClip(root,clip,node=>{
  let owner=node;
  while(owner.parent&&owner.parent!==root&&(/^(bone|joint)([._0-9]|$)/i.test(owner.name)||owner instanceof THREE.Bone))owner=owner.parent;
  return owner.name||owner.uuid;
 });
}

function splitClip(root:THREE.Object3D,clip:THREE.AnimationClip,classify:(node:THREE.Object3D)=>string):{parts:MotionPart[];unresolved:string[]}{
 const groups=new Map<string,THREE.KeyframeTrack[]>(),unresolved:string[]=[];
 for(const track of clip.tracks){
  const parsed=THREE.PropertyBinding.parseTrackName(track.name);
  const node=THREE.PropertyBinding.findNode(root,parsed.nodeName);
  if(!(node instanceof THREE.Object3D)){unresolved.push(track.name);continue}
  const name=classify(node),tracks=groups.get(name)??[];
  tracks.push(track);groups.set(name,tracks);
 }
 // Missing targets would silently drop a motion. Preserve the source action
 // instead until the mapping is understood.
 if(unresolved.length)return {parts:[{name:'original',clip}],unresolved};
 return {parts:[...groups].map(([name,tracks])=>({name,clip:new THREE.AnimationClip(`${clip.name}:${name}`,clip.duration,tracks,clip.blendMode)})),unresolved};
}

// Opt-in audit: compare the recomposed clip to the original on independent
// skeletons at several poses. This is not a comparison with the filmed video.
export function auditHeroParts(root:THREE.Object3D,source:THREE.AnimationClip,parts:MotionPart[]){
 const original=clone(root),reassembled=clone(root);
 const a=new THREE.AnimationMixer(original),b=new THREE.AnimationMixer(reassembled);
 const action=a.clipAction(source).play(),actions=parts.map(part=>b.clipAction(part.clip).play());
 action.paused=true;for(const item of actions)item.paused=true;
 const left:THREE.Object3D[]=[],right:THREE.Object3D[]=[];
 original.traverse(node=>left.push(node));reassembled.traverse(node=>right.push(node));
 let maximum=0;
 for(const fraction of [0,.1,.25,.5,.75,.9,.999]){
  action.time=source.duration*fraction;for(const item of actions)item.time=action.time;
  a.update(0);b.update(0);
  for(let i=0;i<left.length;i++){
   const q=left[i].quaternion,r=right[i].quaternion;
   maximum=Math.max(maximum,left[i].position.distanceTo(right[i].position),left[i].scale.distanceTo(right[i].scale),Math.abs(q.x-r.x),Math.abs(q.y-r.y),Math.abs(q.z-r.z),Math.abs(q.w-r.w));
  }
 }
 a.stopAllAction();b.stopAllAction();
 return {samples:7,nodes:left.length,maximumTransformDifference:maximum};
}
