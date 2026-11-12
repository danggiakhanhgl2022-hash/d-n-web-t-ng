/* Two-render transition with luminance edges, original mud normal and periodic
   noise. Rotation belongs to the 3D camera, not a finite screen texture. */
export const cinemaRevealFragment=`
uniform sampler2D tDiffuse;
uniform sampler2D previous;
uniform sampler2D mudNormal;
uniform sampler2D noiseMap;
uniform float progress;
uniform float opening;
uniform float aspect;
uniform float clock;
uniform float radialTransition;
uniform vec2 centre;
varying vec2 vUv;
// Tăng độ rực: ACES làm nhạt màu, bù lại bằng độ bão hòa và chút tương phản (trước bước chuyển sang sRGB).
vec3 grade(vec3 c){
 float l=dot(c,vec3(.299,.587,.114));
 vec3 v=mix(vec3(l),c,1.16);
 v=pow(max(v,vec3(0.)),vec3(1.05))*1.05;
 return max(v,vec3(0.));
}
vec3 lines(vec3 color,float gain){
 float luma=dot(color,vec3(.299,.587,.114));
 return vec3(clamp(fwidth(luma)*gain,0.,1.8));
}
void main(){
 vec4 next=texture2D(tDiffuse,vUv);
 if(opening>=.999 && progress>=.999){gl_FragColor=vec4(grade(next.rgb),1.);return;}
 vec2 aspectUV=vUv*vec2(aspect,1.);
 float n=texture2D(noiseMap,aspectUV*.25+vec2(-clock*.00875,clock*.02)).r*2.-1.;
 vec3 mud=texture2D(mudNormal,vUv*2.).rgb;
 float strength=mix(.2,.4,.5+.5*sin(clock-vUv.x*10.));
 float surface=n*.1+(mud.r-.5)*strength*.5;
 vec4 scene=next;
 if(progress<.999){
  float t=progress*progress*(3.-2.*progress);
  vec2 oldUV=vUv,newUV=vUv;
  if(radialTransition>.5){
   oldUV=(vUv-centre)*(1.-smoothstep(.2,1.,progress)*.08)+centre;
   newUV=(vUv-centre)*(1.+(1.-smoothstep(0.,.8,progress))*.08)+centre;
  }
  vec4 old=texture2D(previous,oldUV);
  next=texture2D(tDiffuse,newUV);
  vec3 oldLines=lines(old.rgb,mix(5.,10.,t));
  vec3 newLines=lines(next.rgb,mix(10.,5.,t));
  // In the reference the first part of the Sidekick wipe is a dark,
  // sparkling void; the incoming portrait's outlines resolve afterwards.
  if(radialTransition>.5){
   vec2 cell=floor(vUv*vec2(720.,480.));
   float speck=step(.997,fract(sin(dot(cell,vec2(12.9898,78.233)))*43758.5453));
   newLines=newLines*smoothstep(.52,.82,progress)+vec3(speck*.65*(1.-smoothstep(.38,.72,progress)));
  }
  if(radialTransition<.5)old=mix(old,vec4(oldLines,1.),smoothstep(0.,.5,t));
  // The reference keeps the incoming figure as white contours until late
  // in the wipe; early colour made the portrait appear before the source.
  next=mix(next,vec4(newLines,1.),1.-smoothstep(.55,.95,progress));
  float threshold=mix(vUv.y,vUv.x,.38)+surface;
  float advance=mix(-.15,1.15,t);
  if(radialTransition>.5){
   float distance=length((vUv-centre)*vec2(aspect,1.));
   vec2 extent=max(centre,vec2(1.)-centre)*vec2(aspect,1.);
   threshold=distance+surface;
   advance=mix(-.12,length(extent)+.16,t);
  }
  float edge=advance-threshold;
  float aa=max(fwidth(edge)*2.,.003);
  if(radialTransition>.5){
   // Keep the untouched outskirts in colour. The old scene becomes an
   // outline only in a narrow band as the advancing dissolve reaches it.
   float oldEdge=(1.-smoothstep(.015,.18,abs(edge)))*smoothstep(.1,.35,progress);
   old=mix(old,vec4(oldLines,1.),oldEdge*.8);
  }
  scene=mix(old,next,smoothstep(-aa,aa,edge));
  float band=1.-smoothstep(0.,.012,abs(edge));
  float gain=mix(5.,10.,.5+.5*n*sin(clock+vUv.x*10.));
  // Multiplication alone leaves a black pixel black. An additive rim keeps
  // the expanding boundary visible across the dark Sidekick background too.
  float pulse=sin(3.14159265*t);
  vec3 rimLight=vec3(.55,.52,.48)*band*pulse*(.55+.45*mud.g);
  scene.rgb=mix(scene.rgb,scene.rgb*gain,band)+rimLight;
  if(radialTransition>.5){
   // The photographed transition begins with a brief central flash before
   // the dark star field and broken bright edge expand outwards.
   float r=length((vUv-centre)*vec2(aspect,1.));
   float flash=smoothstep(0.,.07,progress)*(1.-smoothstep(.13,.3,progress));
   float glow=exp(-r*r/mix(.001,.016,smoothstep(0.,.2,progress)));
   scene.rgb+=vec3(1.,.91,.84)*glow*flash*1.6;
  }
 }
 if(opening<.999){
  // The recording grows from an upper patch into uneven lobes, rather than
  // a uniformly expanding disc. Macro shape and fine mud use separate scales.
  vec2 revealCentre=centre+vec2(.035*sin(opening*3.14159265),.14*(1.-opening));
  vec2 p=(vUv-revealCentre)*vec2(aspect,1.);
  // The photographed hole is taller than wide and leans slightly: tilt, then stretch vertically.
  float tilt=-.28;
  p=vec2(cos(tilt)*p.x-sin(tilt)*p.y,sin(tilt)*p.x+cos(tilt)*p.y)*vec2(1.,.78);
  float angle=atan(p.y,p.x);
  float macro=sin(angle*3.+opening*2.8)*.055+sin(angle*5.-opening*3.4)*.025;
  float broad=texture2D(noiseMap,vUv*vec2(aspect,1.)*1.6+vec2(opening*.13,-opening*.09)).r-.5;
  float shapeEnvelope=sin(opening*3.14159265);
  float distance=length(p)+surface+(macro+broad*.18)*shapeEnvelope;
  vec2 extent=max(revealCentre,vec2(1.)-revealCentre)*vec2(aspect,1.);
  float spread=opening;
  float edge=mix(-.12,length(extent)+.15,spread);
  float aa=max(fwidth(distance)*2.,.002);
  float mask=smoothstep(distance-aa,distance+aa,edge);
  float rim=1.-smoothstep(0.,.014,abs(distance-edge));
  float halo=1.-smoothstep(.008,.045,abs(distance-edge));
  vec3 detail=lines(scene.rgb,8.);
  vec3 light=(detail+vec3(.22,.205,.18))*rim*(2.+mud.g*2.)+vec3(.19,.16,.15)*halo;
  // Inside the hole the recording is brighter and more saturated pink than the
  // plain render; it relaxes as the hole fills the screen.
  float lift=1.+.6*(1.-smoothstep(.25,.95,opening));
  float luma=dot(scene.rgb,vec3(.299,.587,.114));
  vec3 vivid=mix(vec3(luma),scene.rgb,1.28)*lift+vec3(.06,.025,.03)*(lift-1.);
  // Soft bloom: wide warm glow just inside the edge, faint pink glow outside.
  float e=edge-distance;
  float glowEnv=smoothstep(0.,.05,opening)*(1.-smoothstep(.7,1.,opening));
  float inner=exp(-max(e,0.)/.055)*step(0.,e);
  float outer=exp(-max(-e,0.)/.028)*step(0.,-e);
  vec3 bloomLight=(vec3(1.,.9,.84)*inner*.5+vec3(1.,.62,.7)*outer*.4)*glowEnv;
  // Early on the hole is a small white-hot spot.
  float spot=exp(-dot(p,p)/.0016)*smoothstep(.0,.03,opening)*(1.-smoothstep(.05,.16,opening));
  scene.rgb=vivid*mask+light*.55+bloomLight+vec3(1.,.95,.9)*spot*1.4;
 }
 gl_FragColor=vec4(grade(scene.rgb),1.);
}`;
