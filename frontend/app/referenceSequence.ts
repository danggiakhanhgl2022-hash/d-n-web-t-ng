// Observed video boundaries, reviewed on 0.1-second frames. These describe
// the recording; normal browsing remains scroll driven after the opening.
export const REFERENCE_SEQUENCE=[
 {id:'hero',start:0,end:5.95,paperAt:null,travel:145},
 {id:'sidekick',start:5.95,end:10.1,paperAt:9.2,travel:155},
 {id:'agentic',start:10.1,end:13.1,paperAt:12.1,travel:130},
 {id:'online',start:13.1,end:18.2,paperAt:14.4,travel:110},
 {id:'retail',start:18.2,end:23,paperAt:21.8,travel:185},
 {id:'marketing',start:23,end:25.1,paperAt:23.8,travel:95},
 {id:'checkout',start:25.1,end:26.4,paperAt:25.7,travel:80},
 {id:'operations',start:26.4,end:28.4,paperAt:26.9,travel:90},
 {id:'shop-app',start:28.4,end:29.8,paperAt:29.1,travel:85},
 {id:'b2b',start:29.8,end:31.2,paperAt:30.5,travel:85},
 {id:'finance',start:31.2,end:32.9,paperAt:32.3,travel:100},
 {id:'shipping',start:32.9,end:34.1,paperAt:33.5,travel:80},
 {id:'developer',start:34.1,end:1040/30,paperAt:34.5,travel:75},
] as const;
export const INTRO_SECONDS=3.2;
// Bản mẫu chạy rất nhanh; kéo chậm phần mở đầu và chuyển cảnh để dễ nhìn (1 = đúng tốc độ video).
export const INTRO_SLOWDOWN=2.2;
export const SCENE_TRANSITION_MS=1250;
export function mapClock(seconds:number,keys:readonly(readonly[number,number])[]):number{
 if(seconds<=keys[0][0])return keys[0][1];
 // Shape-preserving cubic interpolation keeps key poses and monotonicity,
 // while matching velocity on both sides of each measured time marker.
 const tangent=(i:number)=>{
  if(i===0||i===keys.length-1)return 0;
  const a=keys[i-1],b=keys[i],c=keys[i+1],left=(b[1]-a[1])/(b[0]-a[0]),right=(c[1]-b[1])/(c[0]-b[0]);
  if(left*right<=0)return 0;
  const w1=2*(c[0]-b[0])+(b[0]-a[0]),w2=(c[0]-b[0])+2*(b[0]-a[0]);
  return (w1+w2)/(w1/left+w2/right);
 };
 for(let i=1;i<keys.length;i++)if(seconds<=keys[i][0]){
  const a=keys[i-1],b=keys[i],span=b[0]-a[0],t=(seconds-a[0])/span,t2=t*t,t3=t2*t;
  return (2*t3-3*t2+1)*a[1]+(t3-2*t2+t)*span*tangent(i-1)+(-2*t3+3*t2)*b[1]+(t3-t2)*span*tangent(i);
 }
 return keys[keys.length-1][1];
}
// Aperture and camera sampled against 0.1s source contacts. Mask values are
// a calibrated reconstruction, not recovered original shader uniforms.
// 0.05s review: first bright patch at source F5 (0.167s), then the
// opening expands before the right sleeve becomes visible around F26.
// Values describe a reconstruction of the mask, not measured uniforms.
export const APERTURE_KEYS=[[0,0],[.05,0],[.1,0],[.15,.035],[.2,.12],[.25,.18],[.3,.24],[.35,.29],[.4,.34],[.45,.4],[.5,.45],[.55,.49],[.6,.52],[.65,.56],[.7,.6],[.75,.64],[.8,.68],[.85,.73],[.9,.78],[.95,.83],[1,.87],[1.05,.91],[1.1,.94],[1.15,.97],[1.2,1]] as const;
// The recorded reference still crops most faces near 1.0s. The prior camera
// approached its final pose too soon; extend the approach without changing rig keys.
export const CAMERA_KEYS=[[0,0],[.2,.16],[.5,.4],[.9,.68],[1,.72],[1.3,.74],[1.5,.83],[1.8,1],[3.2,1]] as const;
// Source contacts still crop the figures at 1.3s; they settle into the full
// composition near 1.8s. Delay the rig independently of the aperture/camera.
// These are reconstruction keys, not animation data recovered from the video.
export const RIG_KEYS=[[0,0],[.8,.6],[1.1,1],[1.3,1.15],[1.5,1.5],[1.7,1.767],[1.75,1.767],[2.05,2.467],[3.2,2.467]] as const;
