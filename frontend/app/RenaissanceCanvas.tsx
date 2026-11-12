"use client";
import {useEffect,useRef} from "react";
import * as THREE from "three";
import {GLTFLoader} from "three/addons/loaders/GLTFLoader.js";
import {DRACOLoader} from "three/addons/loaders/DRACOLoader.js";
import {KTX2Loader} from "three/addons/loaders/KTX2Loader.js";
import {MeshoptDecoder} from "three/addons/libs/meshopt_decoder.module.js";
import {EffectComposer} from "three/addons/postprocessing/EffectComposer.js";
import {RenderPass} from "three/addons/postprocessing/RenderPass.js";
import {UnrealBloomPass} from "three/addons/postprocessing/UnrealBloomPass.js";
import {OutputPass} from "three/addons/postprocessing/OutputPass.js";
import {ShaderPass} from "three/addons/postprocessing/ShaderPass.js";
import {objectAt,type SceneState} from "./sceneTimeline";
import {cinemaRevealFragment} from "./cinemaReveal";
import {createRevealNoise} from "./revealNoise";
import {INTRO_SECONDS,INTRO_SLOWDOWN,SCENE_TRANSITION_MS,mapClock,APERTURE_KEYS,CAMERA_KEYS,RIG_KEYS} from "./referenceSequence";
import {auditHeroParts,splitHeroClip,splitObjectClip,type MotionPart} from "./heroMotionParts";
export type CinemaScene={id:string;title:string;timeline:string;assets:string[];fallback:string;customCamera?:string};
type Asset={root:THREE.Object3D; mixer?:THREE.AnimationMixer;clips:THREE.AnimationClip[];video?:HTMLVideoElement;parts?:Map<string,MotionPart[]>;partReports?:Record<string,unknown>[]};
type Loaded={scene:THREE.Scene;state:SceneState;assets:Asset[];particles?:THREE.Points};
type Values={position?:{x?:number;y?:number;z?:number};rotation?:{x?:number;y?:number;z?:number};scale?:{x?:number;y?:number;z?:number};visibility?:number;fov?:number;target?:{x?:number;y?:number;z?:number};animations?:Record<string,{progress?:number;base?:number;autoplay?:number;mode?:string;loop?:boolean}>;timeline?:number;frameProgress?:number;frame?:number};
function apply(root:THREE.Object3D,v:Values){
 if(v.position)root.position.set(v.position.x??0,v.position.y??0,v.position.z??0);
 if(v.rotation)root.rotation.set(v.rotation.x??0,v.rotation.y??0,v.rotation.z??0);
 if(v.scale)root.scale.set(v.scale.x??1,v.scale.y??1,v.scale.z??1);
 root.visible=(v.visibility??1)>.005;
}
function disposeScene(scene:THREE.Scene){scene.traverse(node=>{if(node instanceof THREE.Mesh||node instanceof THREE.Points){node.geometry.dispose();for(const material of Array.isArray(node.material)?node.material:[node.material]){for(const value of Object.values(material))if(value instanceof THREE.Texture)value.dispose();material.dispose()}}})}
export default function RenaissanceCanvas({scenes,active,progress,opening,onStatus}:{scenes:CinemaScene[];active:number;progress:number;opening:number;onStatus:(status:string)=>void}){
 const host=useRef<HTMLDivElement>(null),position=useRef({active,progress,opening}),status=useRef(onStatus);
 position.current={active,progress,opening};status.current=onStatus;
 useEffect(()=>{
  if(!host.current||!scenes.length)return;
  const node=host.current;let renderer:THREE.WebGLRenderer;
  const tr=(m:string)=>{const w=window as unknown as {__cinemaTrace?:string[]};(w.__cinemaTrace=w.__cinemaTrace||[]).push(m+'@'+Math.round(performance.now()))};
  let readyLogged=false;
  const why=(m:string)=>{(window as unknown as {__cinemaWhy?:string}).__cinemaWhy=m;console.warn('[cinema] fallback:',m)};
  // Không có WebGL2: dùng ảnh dự phòng ngay, không dựng cảnh 3D.
  const nav=navigator as Navigator&{deviceMemory?:number};
  let hasGl2=false;try{hasGl2=!!document.createElement("canvas").getContext("webgl2")}catch{}
  const veryWeak=!hasGl2;
  if(veryWeak){{why('c1');status.current("fallback")};return}
  // Máy trung bình / điện thoại: tắt khử răng cưa và giảm độ phân giải.
  const lowTier=/Android|iPhone|iPad|Mobile/i.test(navigator.userAgent)||(nav.deviceMemory!==undefined&&nav.deviceMemory<=4)||(nav.hardwareConcurrency!==undefined&&nav.hardwareConcurrency<=4);
  try{renderer=new THREE.WebGLRenderer({alpha:true,antialias:!lowTier,powerPreference:"high-performance"})}catch{{why('c2');status.current("fallback")};return}
  renderer.setPixelRatio(1);renderer.outputColorSpace=THREE.SRGBColorSpace;renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1;
  renderer.debug.onShaderError=()=>{why('c3');status.current('fallback')};
  node.appendChild(renderer.domElement);tr('renderer');
  const draco=new DRACOLoader().setDecoderPath('/renaissance/3d/draco/gltf/');
  const ktx=new KTX2Loader().setTranscoderPath('/renaissance/3d/basis/').detectSupport(renderer);
  const loader=new GLTFLoader().setDRACOLoader(draco).setKTX2Loader(ktx).setMeshoptDecoder(MeshoptDecoder);
  const cache=new Map<number,Loaded>(),pending=new Set<number>(),failed=new Set<number>();
  const camera=new THREE.PerspectiveCamera(25,1,.01,1000),origin=performance.now();
  const composer=new EffectComposer(renderer),renderPass=new RenderPass(new THREE.Scene(),camera),bloom=new UnrealBloomPass(new THREE.Vector2(1,1),.12,.35,1.15);
  const previousFrame=new THREE.WebGLRenderTarget(1,1);
  const noiseTexture=createRevealNoise();
  const neutralMud=new THREE.DataTexture(new Uint8Array([128,128,255,255]),1,1,THREE.RGBAFormat);neutralMud.needsUpdate=true;
  let mudTexture:THREE.Texture=neutralMud;
  const transition=new ShaderPass({uniforms:{tDiffuse:{value:null},previous:{value:null},mudNormal:{value:neutralMud},noiseMap:{value:noiseTexture},progress:{value:1},opening:{value:0},aspect:{value:1},clock:{value:0},radialTransition:{value:0},centre:{value:new THREE.Vector2(.5,.5)}},vertexShader:'varying vec2 vUv; void main(){vUv=uv;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0);}',fragmentShader:cinemaRevealFragment});
  transition.uniforms.previous.value=previousFrame.texture;
  composer.addPass(renderPass);composer.addPass(transition);composer.addPass(bloom);composer.addPass(new OutputPass());
  let lastScene:THREE.Scene|undefined,lastCamera:THREE.Camera|undefined,lastDrawn=-1,transitionStart=0,transitionElapsed=0,transitionTick=0;
  const videos=new Set<HTMLVideoElement>();
  let ended=false,frame=0,visible=true,last=-1,heroIdleStart:number|null=null;const pointer=new THREE.Vector2();
  // Theo dõi tốc độ khung hình: nếu máy gần như đứng hình (dưới ~5 fps trong 6 giây sau khi tải xong) thì chuyển sang ảnh dự phòng.
  let wdFrames=0,wdStart=0,wdId=0;
  const watchdog=(now:number)=>{
   if(ended)return;
   if(document.hidden){wdFrames=0;wdStart=0}
   else{
    if(!wdStart)wdStart=now;wdFrames++;
    if(now-wdStart>=6000){
     const fps=wdFrames*1000/(now-wdStart);
     if(fps<5&&!matchMedia('(prefers-reduced-motion: reduce)').matches){{why('c4');status.current('fallback')};return}
     wdFrames=0;wdStart=now;
    }
   }
   wdId=requestAnimationFrame(watchdog);
  };
  const wdTimer=window.setTimeout(()=>{wdId=requestAnimationFrame(watchdog)},4000);
  let ringPhase=-1,ringLastScroll=0,ringIdleWeight=0;
  const mudReady=new THREE.TextureLoader().loadAsync('/renaissance/3d/mud_normal.webp').then(texture=>{
   if(ended){texture.dispose();return}
   texture.wrapS=texture.wrapT=THREE.RepeatWrapping;
   mudTexture=texture;transition.uniforms.mudNormal.value=texture;
   renderer.domElement.dataset.revealSurface='reference';
  }).catch(()=>{renderer.domElement.dataset.revealSurface='fallback'});
  const reduced=matchMedia('(prefers-reduced-motion: reduce)');
  window.addEventListener('scroll',()=>{(window as any).__lastScroll=performance.now()},{passive:true});const resize=()=>{renderer.setSize(node.clientWidth,node.clientHeight);composer.setSize(node.clientWidth,node.clientHeight);const dimensions=renderer.getDrawingBufferSize(new THREE.Vector2());previousFrame.setSize(dimensions.x,dimensions.y);camera.aspect=node.clientWidth/Math.max(1,node.clientHeight);camera.updateProjectionMatrix();transition.uniforms.aspect.value=camera.aspect};
  resize();const observer=new ResizeObserver(resize);observer.observe(node);
  const move=(e:PointerEvent)=>{pointer.set(e.clientX/innerWidth-.5,e.clientY/innerHeight-.5)};
  const visibility=()=>{visible=!document.hidden};document.addEventListener('visibilitychange',visibility);window.addEventListener('pointermove',move,{passive:true});
  const contextLost=(e:Event)=>{e.preventDefault();{why('c5');status.current('fallback')}};renderer.domElement.addEventListener('webglcontextlost',contextLost);
  const load=async(index:number)=>{
   if(index<0||index>=scenes.length||cache.has(index)||pending.has(index)||failed.has(index))return;
   pending.add(index);tr('load'+index);
   const scene=new THREE.Scene();
   try{
    const config=scenes[index];const response=await fetch(config.timeline);if(!response.ok)throw Error('timeline');const state=await response.json() as SceneState;tr('timeline'+index);
    const assets=await Promise.all(config.assets.map(async(url):Promise<Asset>=>{
     if(url.endsWith('.glb')){
      const gltf=await loader.loadAsync(url);
      if(config.id==='sidekick')gltf.scene.traverse(object=>{
       if(!(object instanceof THREE.Mesh)||!object.name.startsWith('shiny-ring'))return;
       for(const material of Array.isArray(object.material)?object.material:[object.material]){
        // This local scene has no environment map; fully metallic rings were
        // almost black even though the reference shows their gold edges.
        if(material instanceof THREE.MeshStandardMaterial){material.metalness=Math.min(material.metalness,.5);material.emissive.setRGB(.014,.007,.002)}
       }
      });
      if(config.id==='retail'&&url.includes('POS_v53_Hub'))gltf.scene.traverse(object=>{
       if(!(object instanceof THREE.Mesh))return;
       for(const material of Array.isArray(object.material)?object.material:[object.material]){
        // The local model lacks the reference environment reflections. Lift
        // the two shell materials enough to reveal their form and port edges.
        // This is a visual reconstruction, not the reference lighting data.
        if(material instanceof THREE.MeshStandardMaterial&&['pos-hub-shell','pos-hub-bottom'].includes(material.name))material.emissive.setRGB(.09,.09,.09);
       }
      });
      const root=new THREE.Group();root.add(gltf.scene);
      const parts=new Map<string,MotionPart[]>(),partReports:Record<string,unknown>[]=[];
      for(const clip of gltf.animations){
       // Playback uses the source clip directly. Splitting identical-time tracks
       // is useful for audit, but creates many redundant actions in production.
       const split=new URLSearchParams(location.search).has('motionAudit')?(config.id==='hero'?splitHeroClip(gltf.scene,clip):splitObjectClip(gltf.scene,clip)):{parts:[{name:'original',clip}],unresolved:[]};parts.set(clip.uuid,split.parts);
       partReports.push({clip:clip.name,asset:url.split('/').pop(),sourceTracks:clip.tracks.length,unresolved:split.unresolved,parts:Object.fromEntries(split.parts.map(part=>[part.name,part.clip.tracks.length])),...(new URLSearchParams(location.search).has('motionAudit')?{audit:auditHeroParts(gltf.scene,clip,split.parts)}:{})});
      }
      return {root,mixer:new THREE.AnimationMixer(gltf.scene),clips:gltf.animations,parts,partReports};
     }
     if(url.endsWith('.json')){
      const descriptor=await fetch(url).then(r=>r.json());
      const video=document.createElement('video');video.src=descriptor.url;video.muted=true;video.playsInline=true;video.preload='auto';video.loop=true;videos.add(video);
      const texture=new THREE.VideoTexture(video);texture.colorSpace=THREE.SRGBColorSpace;
      // Theatre planes use the same UV convention as the KTX fallback.
      // VideoTexture defaults to flipY=true and inverted the skateboard film.
      texture.flipY=false;
      const root=new THREE.Mesh(new THREE.PlaneGeometry(2,2),new THREE.MeshBasicMaterial({map:texture,side:THREE.DoubleSide,transparent:true,depthWrite:false}));
      // Paused videos are scrubbed by the scene timeline. Explicitly upload
      // decoded seek frames; do not rely on playback callbacks for GPU updates.
      const refresh=()=>{if(video.readyState>=HTMLMediaElement.HAVE_CURRENT_DATA)texture.needsUpdate=true};
      video.addEventListener('loadeddata',refresh);video.addEventListener('seeked',refresh);
      // Keep a decoded image visible while the first video frame is loading.
      if(descriptor.fallbackImage){void ktx.loadAsync(descriptor.fallbackImage).then(fallback=>{
       if(ended){fallback.dispose();return}fallback.colorSpace=THREE.SRGBColorSpace;
       if(video.readyState<HTMLMediaElement.HAVE_CURRENT_DATA){root.material.map=fallback;root.material.needsUpdate=true}
       const swap=()=>{root.material.map=texture;root.material.needsUpdate=true;refresh();fallback.dispose()};
       if(video.readyState>=HTMLMediaElement.HAVE_CURRENT_DATA)swap();else video.addEventListener('loadeddata',swap,{once:true});
      }).catch(()=>{})}
      video.addEventListener('loadedmetadata',()=>{root.geometry.dispose();root.geometry=new THREE.PlaneGeometry(2*video.videoWidth/Math.max(1,video.videoHeight),2);
       // Marketing's freestanding billboard is upright, unlike the rotated
       // background/video planes. Correct its UVs without rotating its rig.
       if(config.id==='marketing'){const uv=root.geometry.getAttribute('uv');for(let j=0;j<uv.count;j++)uv.setY(j,1-uv.getY(j));uv.needsUpdate=true}
      },{once:true});
      video.load();return {root,clips:[],video};
     }
     const texture=await ktx.loadAsync(url);texture.colorSpace=THREE.SRGBColorSpace;
     const root=new THREE.Mesh(new THREE.PlaneGeometry(2*texture.image.width/texture.image.height,2),new THREE.MeshBasicMaterial({map:texture,side:THREE.DoubleSide,depthWrite:false}));
     return {root,clips:[]};
    }));
    for(const asset of assets)scene.add(asset.root);
    scene.add(new THREE.HemisphereLight(0xffffff,0x44354a,.25));const key=new THREE.DirectionalLight(0xffefdc,.35);key.position.set(3,5,5);scene.add(key);
    const particleSettings=objectAt(state,'particles',1) as {enabled?:boolean;count?:number;color?:{r:number;g:number;b:number};scale?:{x:number;y:number;z:number};position?:{x?:number;y?:number;z?:number};size?:number};
    let particles:THREE.Points|undefined;
    if(particleSettings.enabled){
     const count=Math.min(particleSettings.count??200,500),positions=new Float32Array(count*3);let seed=12345;
     const random=()=>{seed=(seed*16807)%2147483647;return seed/2147483647-.5};
     for(let j=0;j<count;j++){positions[j*3]=random()*(particleSettings.scale?.x??5);positions[j*3+1]=random()*(particleSettings.scale?.y??5);positions[j*3+2]=random()*(particleSettings.scale?.z??5)}
     const geometry=new THREE.BufferGeometry();geometry.setAttribute('position',new THREE.BufferAttribute(positions,3));
     const color=particleSettings.color;
     particles=new THREE.Points(geometry,new THREE.PointsMaterial({color:color?new THREE.Color(color.r,color.g,color.b):0xffdf9c,size:(particleSettings.size??.1)*.05,transparent:true,opacity:.55,depthWrite:false,blending:THREE.AdditiveBlending}));
     particles.position.set(particleSettings.position?.x??0,particleSettings.position?.y??0,particleSettings.position?.z??0);scene.add(particles);
    }
    for(const asset of assets)for(const clip of asset.clips)for(const part of asset.parts?.get(clip.uuid)??[{name:'original',clip}])asset.mixer?.clipAction(part.clip).play();
    await mudReady;tr('mud'+index);
    if(ended||Math.abs(position.current.active-index)>1){disposeScene(scene);return}
    // Compile the opening rig before starting its clock, avoiding shader work
    // competing with the first visible animation frames.
    if(index===0)try{await renderer.compileAsync(scene,camera)}catch{}
    if(ended){disposeScene(scene);return}cache.set(index,{scene,state,assets,particles});tr('cached'+index);
    // Làm nóng trước cảnh vừa tải (biên dịch shader, đẩy texture lên GPU từng cái một) để lúc chuyển slide không bị khựng.
    if(index!==0)try{void renderer.compileAsync(scene,camera).catch(()=>{})}catch{}
    {const maps:THREE.Texture[]=[];scene.traverse(o=>{const m=(o as THREE.Mesh).material as THREE.Material|THREE.Material[]|undefined;for(const mat of Array.isArray(m)?m:m?[m]:[])for(const v of Object.values(mat as unknown as Record<string,unknown>))if(v instanceof THREE.Texture&&!(v instanceof THREE.VideoTexture)&&!maps.includes(v)){v.anisotropy=Math.max(v.anisotropy,Math.min(16,renderer.capabilities.getMaxAnisotropy()));maps.push(v)}});
    let n=0;const step=()=>{if(ended||n>=maps.length)return;try{renderer.initTexture(maps[n++])}catch{}setTimeout(step,24)};setTimeout(step,200)}
   }catch(error){disposeScene(scene);failed.add(index);console.warn('Reference scene unavailable',scenes[index].id,error);if(position.current.active===index){why('c6');status.current('fallback')}}
   finally{pending.delete(index)}
  };
  let nFrames=0,dbgReason='';
  const dbg=(r:string)=>{if(dbgReason!==r){dbgReason=r;tr('f'+nFrames+':'+r)}};
  // Bộ tự điều chỉnh chất lượng: nếu máy chậm thì tự hạ độ phân giải và tắt bloom cho mượt.
  let gvLast=0,gvEma=16,gvPr=renderer.getPixelRatio(),gvCool=0,gvBloomOff=false,gvStart=performance.now();
  const governor=()=>{
   const now=performance.now();if(!gvLast){gvLast=now;return}
   const dt=Math.min(100,now-gvLast);gvLast=now;
   // Bỏ qua giai đoạn nạp/biên dịch (đầu trang) để không hạ độ nét nhầm.
   if(nFrames<300||!readyLogged||now<gvStart+6000){gvEma=16;return}
   gvEma=gvEma*.95+dt*.05;
   if(gvCool>0){gvCool--;return}
   if(gvEma>34&&gvPr>.9){gvPr=Math.max(.9,gvPr-.15);renderer.setPixelRatio(gvPr);resize();gvCool=180;gvEma=16;if(gvPr<=1.05)gvBloomOff=true}
  };

  let lastRenderedAt=0,nextSceneQueued=false,openingClockStart:number|null=null;
  const render=()=>{
   nFrames++;if(ended){dbg('ended');return}frame=requestAnimationFrame(render);if(!visible){dbg('hidden');gvLast=0;return}
   const frameNow=performance.now();
   if(lowTier&&frameNow-lastRenderedAt<32)return;
   lastRenderedAt=frameNow;
   governor();
   const {active:index,progress:phase}=position.current;
   // React updates the UI opening state in coarse steps. Never use that
   // state as the camera clock: .02 steps over 7 seconds produce ~7 fps poses.
   const arrival=reduced.matches?1:openingClockStart===null?0:Math.min(1,(frameNow-openingClockStart)/(INTRO_SECONDS*INTRO_SLOWDOWN*1000));
   if(last!==index){
    ringPhase=-1;ringIdleWeight=0;ringLastScroll=performance.now();
    if(lastScene&&lastCamera){renderer.setRenderTarget(previousFrame);renderer.clear();renderer.render(lastScene,lastCamera);renderer.setRenderTarget(null)}
    transitionStart=lastDrawn<0?-Infinity:performance.now();
    // Keep the previously rendered canvas visible while a later scene loads.
    // The public loading state hides the canvas and is only appropriate for
    // the initial scene; using it here caused a dark/static flash between pages.
    if(!lastScene)status.current('loading');
    node.closest<HTMLElement>('.renaissance-cinema')?.style.setProperty('--scene-arrival','0');
    last=index;void load(index);if(index>0)void load(index+1);
    for(const [key,value] of cache)if(Math.abs(key-index)>1){disposeScene(value.scene);cache.delete(key)}
   }
   if(index===0&&!nextSceneQueued&&(arrival>=1||phase>.01)){nextSceneQueued=true;void load(1)}
   const loaded=cache.get(index);if(!loaded){dbg('noscene'+index);if(lastDrawn<0)renderer.clear();if(failed.has(index)){why('c7');status.current('fallback')};return}
   if(openingClockStart===null)openingClockStart=frameNow;
   if(lastDrawn!==index){
    // A scene may finish loading after the transition clock has already run
    // out. Preserve most of the transition so it remains visible on slow loads.
    const now=performance.now();
    transitionElapsed=lastDrawn<0?SCENE_TRANSITION_MS:Math.min(SCENE_TRANSITION_MS*.2,Math.max(0,now-transitionStart));
    transitionTick=now;
    transition.uniforms.progress.value=lastDrawn<0?1:0;lastDrawn=index;
   }
   // Original timeline units are seconds; the scene's useful camera tracks occupy its opening segment.
   const sheet=loaded.state.sheetsById.Scene||Object.values(loaded.state.sheetsById)[0];
   const cameraTracks=sheet.sequence.tracksByObject.camera;
   const ends=cameraTracks?Object.values(cameraTracks.trackData).flatMap(t=>t.keyframes.map(k=>k.position)):[];
   // Object tracks can outlive camera tracks (for example the Sidekick rings).
   // Sampling only to the final camera key silently truncated those motions.
   const cameraDuration=Math.max(1,...ends);
   const duration=index===1?cameraDuration:Math.max(cameraDuration,sheet.sequence.length||0);
   // Camera completes the source's initial approach at time 1. The rig uses
   // its own source tracks below, so its limbs continue after the camera holds.
   const heroArrival=1;
   const introSeconds=arrival*INTRO_SECONDS;
   const tick=performance.now();
   // GPU stalls or a background tab can create a very large frame delta.
   // Cap individual advances so a slow frame does not skip the entire wipe.
   const frameDelta=Math.min(80,Math.max(0,tick-transitionTick));transitionElapsed+=frameDelta;transitionTick=tick;
   const sceneBlend=reduced.matches||!lastScene?1:Math.min(1,transitionElapsed/SCENE_TRANSITION_MS);
   const sceneEntry=Math.min(duration,index===1?1.133:1)*THREE.MathUtils.smoothstep(sceneBlend,0,1);
   const idleSeconds=Math.max(0,(performance.now()-(Number.isFinite(transitionStart)?transitionStart+SCENE_TRANSITION_MS:origin))/1000);
   // Keep later chapters alive when the user stops scrolling. Sample the
   // source tracks in a small, continuous window, fading this out on scroll.
   const ambient=index>0&&!reduced.matches&&Number.isFinite(idleSeconds)?(1.-Math.cos(idleSeconds*.65))*.09*(1.-phase):0;
   // In the reference Online's artist remains behind the rising paper. The
   // final camera keys otherwise leave the subject before the paper arrives.
   // Keep that last visible pose while the paper covers the scene; its video
   // plane still uses the unmodified scroll progress below.
   const visualPhase=index===3?Math.min(phase,.8):phase;
   const time=reduced.matches?Math.min(index===0?heroArrival:1,duration):index===0?Math.min(duration,mapClock(introSeconds,CAMERA_KEYS)+phase*(duration-heroArrival)):Math.max(0,Math.min(duration,sceneEntry+visualPhase*(duration-Math.min(duration,index===1?1.133:1))+ambient));
   // Sidekick's authored ring keys extend beyond the camera/visibility range.
   // Sample those clip keys independently so the figure is not hidden early.
   const sidekickMotionTime=index===1&&!reduced.matches?Math.min(sheet.sequence.length||duration,sceneEntry+phase*((sheet.sequence.length||duration)-Math.min(duration,1.133))+ambient):time;
   // The rig continues past its extended pose and folds back at source 2.467.
   // Keep this independent of the camera so it does not zoom away prematurely.
   const rigTime=index===0?(reduced.matches?2.467:mapClock(introSeconds,RIG_KEYS)+phase*(duration-2.467)):time;
   const elapsed=(performance.now()-origin)/1000;
   if(index===1){
    if(ringPhase<0||Math.abs(phase-ringPhase)>.001){ringPhase=phase;ringLastScroll=tick}
    const target=!reduced.matches&&sceneBlend>=.99&&tick-ringLastScroll>450?1:0;
    ringIdleWeight+=(target-ringIdleWeight)*(1-Math.exp(-frameDelta/300));
   }
   if(index===0&&arrival>=1&&phase<.001)heroIdleStart??=elapsed;else heroIdleStart=null;
   const inspectedClips:Record<string,number>={};
   const ringTransforms:Record<string,number[]>={};
   loaded.assets.forEach((asset,i)=>{
    const values=objectAt(loaded.state,`asset-${i+1}`,index===0&&i===0?rigTime:time) as Values;apply(asset.root,values);
    const animationValues=index===1&&i===0?objectAt(loaded.state,`asset-${i+1}`,sidekickMotionTime) as Values:values;
    if(asset.video&&Number.isFinite(asset.video.duration)){
     // Some authored video planes use absolute 30fps frame numbers instead
     // of normalized frameProgress (Marketing: -1..151). Honor that track.
     const baseFrame=values.frameProgress??(values.frame!==undefined?Math.max(0,values.frame/30)/Math.max(.001,asset.video.duration):Math.min(.999,phase));
     const playhead=reduced.matches?.5:Math.min(.999,baseFrame+ambient*.4);
     const wanted=playhead*Math.max(0,asset.video.duration-.04);
     if(!asset.video.seeking&&Math.abs(asset.video.currentTime-wanted)>.06)asset.video.currentTime=wanted;
     if(asset.video.readyState>=HTMLMediaElement.HAVE_CURRENT_DATA&&asset.root instanceof THREE.Mesh){const material=asset.root.material as THREE.MeshBasicMaterial;if(material.map instanceof THREE.VideoTexture)material.map.needsUpdate=true}
    }
    for(const clip of asset.clips){
     // Some Theatre keys replace punctuation in glTF names with underscores.
     const normalize=(name:string)=>name.toLowerCase().replace(/[^a-z0-9]/g,'');
     const settings=animationValues.animations?.[clip.name]??animationValues.animations?.[clip.name.replace(/[.\-]/g,'_')]??Object.entries(animationValues.animations??{}).find(([name])=>normalize(name)===normalize(clip.name))?.[1];
     // Sampling exactly at duration with Repeat wraps to frame zero. Preserve
     // the extended end pose instead of snapping the limbs back for one frame.
     const idle=index===0&&i===0&&arrival>=1&&phase<.001&&!reduced.matches;
     const idleElapsed=Math.max(0,elapsed-(heroIdleStart??elapsed));
     const rigProgress=idle?.09+.055*Math.sin(idleElapsed*.8)*THREE.MathUtils.smoothstep(idleElapsed,0,1.2):settings?.progress;
     let actionTime=rigProgress!==undefined?Math.min(clip.duration-.00001,Math.max(0,rigProgress*clip.duration)):settings?.base!==undefined?(settings.base+(reduced.matches?0:elapsed*(settings.autoplay??0)))*clip.duration:settings?.loop?(reduced.matches?0:elapsed%clip.duration):values.timeline!==undefined?values.timeline:(reduced.matches?0:elapsed%clip.duration);
     // Agentic: sách lật trang liên tục (lướt hết các trang rồi lặp) và đồ vật bay lên khỏi sách liên tục.
     // Khi cuộn thì tiến trình cuộn cộng thêm vào; hiệu ứng tự chạy mờ dần khi cuộn xa.
     if(index===2&&(i===2||i===3)&&!reduced.matches&&clip.name==='Scene'){
      const p=Math.max(0,Math.min(1,settings?.progress??actionTime/clip.duration));
      const w=1-Math.min(1,phase*1.5),rate=i===2?.2:.13;
      const q=(p+idleSeconds*rate*w)%1;
      actionTime=Math.min(clip.duration-.00001,Math.max(0,q)*clip.duration);
     }
     if(index===1&&!reduced.matches&&clip.name.includes('RingAction')&&ringIdleWeight>.001){
      // A small idle oscillation keeps the armillary alive at rest; use the
      // authored clip and fade out when scrolling rather than rotating the
      // mesh outside its rig. This timing is an artistic reconstruction.
      const base=Math.max(0,Math.min(clip.duration-.00001,actionTime));
      const direction=base>clip.duration*.5?-1:1;
      actionTime=base+direction*clip.duration*.018*(.5+.5*Math.sin(idleSeconds*.85))*ringIdleWeight;
     }
     for(const part of asset.parts?.get(clip.uuid)??[{name:'original',clip}]){const action=asset.mixer?.clipAction(part.clip);if(action){action.time=actionTime;action.paused=true}}
     if(index>0)inspectedClips[`${i+1}:${clip.name}`]=Number(actionTime.toFixed(4));
     if(index===0&&i===0)renderer.domElement.dataset.rigPose=String(rigProgress??0);
    }
    asset.mixer?.update(0);
    if(index===1&&asset.mixer)for(const clip of asset.clips){
     if(!clip.name.includes('RingAction')||!clip.tracks.length)continue;
     const target=THREE.PropertyBinding.findNode(asset.mixer.getRoot(),THREE.PropertyBinding.parseTrackName(clip.tracks[0].name).nodeName);
     if(target instanceof THREE.Object3D)ringTransforms[clip.name]=[target.quaternion.x,target.quaternion.y,target.quaternion.z,target.quaternion.w].map(n=>Number(n.toFixed(6)));
    }
   });
   renderer.domElement.dataset.motionClips=JSON.stringify(inspectedClips);
   if(index===1)renderer.domElement.dataset.ringTransforms=JSON.stringify(ringTransforms);
   const reports=loaded.assets.flatMap(asset=>asset.partReports??[]);
   renderer.domElement.dataset.sceneParts=JSON.stringify(reports);
   if(index===0&&reports[0])renderer.domElement.dataset.heroParts=JSON.stringify(reports[0]);
   renderer.domElement.dataset.sequenceDuration=String(duration);
   // Camera and object animation have different authored lengths. Using the
   // full 10-second object clock made a ~5-second camera stop halfway through
   // the scroll (especially noticeable in the final Developer chapter).
   const cameraEntry=Math.min(cameraDuration,index===1?1.133:1)*THREE.MathUtils.smoothstep(sceneBlend,0,1);
   const cameraTime=index===0?time:reduced.matches?Math.min(1,cameraDuration):Math.min(cameraDuration,cameraEntry+visualPhase*(cameraDuration-Math.min(cameraDuration,index===1?1.133:1))+ambient);
   const values=objectAt(loaded.state,'camera',cameraTime) as Values;
   camera.position.set(values.position?.x??0,values.position?.y??0,values.position?.z??5);
   camera.fov=values.fov??25;camera.updateProjectionMatrix();
   camera.lookAt(values.target?.x??0,values.target?.y??0,values.target?.z??0);
   if(!reduced.matches){camera.rotateY(pointer.x*.035+Math.sin(elapsed*.22)*.003);camera.rotateX(pointer.y*.018+Math.sin(elapsed*.18)*.002)}
   camera.rotateZ(values.rotation?.z??0);
   let renderCamera:THREE.Camera=camera;
   if(scenes[index].customCamera){const embedded=loaded.scene.getObjectByName(scenes[index].customCamera!);if(embedded instanceof THREE.PerspectiveCamera){embedded.aspect=camera.aspect;embedded.updateProjectionMatrix();renderCamera=embedded}}
   if(loaded.particles&&!reduced.matches)loaded.particles.rotation.y=Math.sin(elapsed*.05)*.12;
   const effects=objectAt(loaded.state,'effects',time) as {bloom?:{intensity?:number}};
   // Source bloom intensity belongs to a different compositor; keep this pass below washout.
   bloom.strength=reduced.matches?0:Math.min(.18,(effects.bloom?.intensity??0)*.035);
   // Bloom rất tốn GPU: tắt trong lúc chuyển cảnh (và trên máy yếu) để không bị giật.
   bloom.enabled=index!==0&&!lowTier&&!gvBloomOff&&sceneBlend>=.999;
   transition.uniforms.progress.value=sceneBlend;
   node.closest<HTMLElement>('.renaissance-cinema')?.style.setProperty('--scene-arrival',String(reduced.matches?1:THREE.MathUtils.smoothstep(sceneBlend,.35,.95)));
   transition.uniforms.radialTransition.value=index<=1?1:0;
   transition.uniforms.opening.value=reduced.matches||index!==0?1:mapClock(introSeconds,APERTURE_KEYS);
   transition.uniforms.clock.value=elapsed;
   const fade=objectAt(loaded.state,'effects',time) as {sectionTransition?:{fadeCenter?:{x?:number;y?:number;z?:number}}};
   const point=fade.sectionTransition?.fadeCenter;
   const centre=new THREE.Vector3(point?.x??0,point?.y??0,point?.z??-7.5).project(renderCamera);
   // During the intro the projected point can lie behind the moving camera,
   // inverting its y coordinate. Keep the aperture near the observed centre.
   transition.uniforms.centre.value.set(index<=1?.5:THREE.MathUtils.clamp(centre.x*.5+.5,.3,.7),index<=1?.52:THREE.MathUtils.clamp(centre.y*.5+.5,.3,.7));
   renderPass.scene=loaded.scene;renderPass.camera=renderCamera;
   try{composer.render()}catch(err){{why('render '+String(err).slice(0,120)+' c8');status.current('fallback')};return}
   if(!readyLogged){readyLogged=true;tr('ready')}status.current('ready');
   lastScene=loaded.scene;lastCamera=renderCamera.clone();
   // Embedded cameras inherit transforms from the asset. A detached clone
   // must retain world space, otherwise the outgoing snapshot jumps viewpoint.
   renderCamera.matrixWorld.decompose(lastCamera.position,lastCamera.quaternion,lastCamera.scale);
   lastCamera.matrixAutoUpdate=false;lastCamera.matrix.copy(renderCamera.matrixWorld);
   lastCamera.updateMatrixWorld(true);
   renderer.domElement.dataset.scene=scenes[index].id;renderer.domElement.dataset.timeline=time.toFixed(3);
   renderer.domElement.dataset.cameraTimeline=cameraTime.toFixed(3);
   renderer.domElement.dataset.cameraPosition=camera.position.toArray().map(n=>n.toFixed(4)).join(',');
   renderer.domElement.dataset.transitionProgress=String(transition.uniforms.progress.value);
   if(index===0){renderer.domElement.dataset.heroProgress=String((objectAt(loaded.state,'asset-1',rigTime) as Values).animations?.Scene?.progress??0);renderer.domElement.dataset.heroTurn=String(values.rotation?.z??0);}
  };
  void load(0);render();
  return()=>{tr('cleanup');ended=true;clearTimeout(wdTimer);cancelAnimationFrame(wdId);cancelAnimationFrame(frame);observer.disconnect();window.removeEventListener('pointermove',move);document.removeEventListener('visibilitychange',visibility);renderer.domElement.removeEventListener('webglcontextlost',contextLost);for(const video of videos){video.pause();video.removeAttribute('src');video.load()}for(const value of cache.values())disposeScene(value.scene);noiseTexture.dispose();neutralMud.dispose();if(mudTexture!==neutralMud)mudTexture.dispose();draco.dispose();ktx.dispose();bloom.dispose();transition.dispose();previousFrame.dispose();composer.dispose();renderer.dispose();renderer.domElement.remove()};
 },[scenes]);
 return <div ref={host} className="cinema-webgl" aria-hidden="true"/>;
}
