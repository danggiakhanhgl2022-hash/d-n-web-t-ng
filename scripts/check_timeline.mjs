import assert from 'node:assert/strict';
import {sample,objectAt} from '../frontend/app/sceneTimeline.ts';
const keys=[{position:0,value:2,connectedRight:true,type:'bezier',handles:[.5,1,.25,0]},{position:2,value:8,type:'bezier',handles:[.75,1,.5,0]}];
assert.equal(sample(keys,-1),2);
assert.equal(sample(keys,3),8);
assert.ok(Math.abs(sample(keys,1)-5)<.001);
assert.equal(sample([{position:0,value:2,connectedRight:false},{position:2,value:8}],1),2);
assert.equal(sample([],1),undefined);
const state={sheetsById:{Scene:{
 staticOverrides:{byObject:{camera:{position:{x:3,y:4}}}},
 sequence:{length:2,tracksByObject:{camera:{trackData:{x:{keyframes:keys}},trackIdByPropPath:{'["position","x"]':'x'}}}}
}}};
assert.equal(objectAt(state,'camera',1).position.y,4);
assert.equal(state.sheetsById.Scene.staticOverrides.byObject.camera.position.x,3);
console.log('Timeline endpoint, bezier, hold and immutable override checks passed.');
