import assert from 'node:assert/strict';
import {mapClock,APERTURE_KEYS,CAMERA_KEYS,RIG_KEYS} from '../frontend/app/referenceSequence.ts';

for(const keys of [APERTURE_KEYS,CAMERA_KEYS,RIG_KEYS]){
 for(const [time,value] of keys)assert.ok(Math.abs(mapClock(time,keys)-value)<1e-9,'Measured pose must stay on its time marker');
 let previous=-Infinity;
 for(let i=0;i<=3200;i++){
  const value=mapClock(i/1000,keys);
  assert.ok(value>=previous-1e-9,'Clock must not reverse or overshoot between rising poses');
  assert.ok(value>=keys[0][1]-1e-9&&value<=keys.at(-1)[1]+1e-9);
  previous=value;
 }
 const eps=1e-6;
 for(const [time] of keys.slice(1,-1)){
  const a=(mapClock(time,keys)-mapClock(time-eps,keys))/eps;
  const b=(mapClock(time+eps,keys)-mapClock(time,keys))/eps;
  assert.ok(Math.abs(a-b)<.005,`Velocity must be continuous at ${time}: ${a} vs ${b}`);
 }
}
console.log('PASS: camera/rig/aperture preserve measured poses, remain monotone and match velocity at joins.');
