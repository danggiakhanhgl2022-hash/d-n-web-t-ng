"use client";

import {useCallback,useEffect,useRef,useState} from "react";
import dynamic from "next/dynamic";
import type {CinemaScene} from './RenaissanceCanvas';
import CinemaCanvasBoundary from './CinemaCanvasBoundary';
const LiveCanvas=dynamic(()=>import('./RenaissanceCanvas'),{ssr:false});
import RenaissanceCinema from "./RenaissanceCinema";

const SCENES=["hero","assistant","gallery","studio","workshop","delivery"];

export function RenaissanceBackdrop({scene=0}:{scene?:number}){
 const root=useRef<HTMLDivElement>(null);
 const [scenes,setScenes]=useState<CinemaScene[]>([]),[status,setStatus]=useState('loading');
 const handleStatus=useCallback((value:string)=>setStatus(previous=>previous==='fallback'?previous:value),[]);
 const failure=useCallback(()=>handleStatus('fallback'),[handleStatus]);
 useEffect(()=>{const controller=new AbortController();fetch('/renaissance/3d/scenes.json',{signal:controller.signal}).then(r=>{if(!r.ok)throw Error('manifest');return r.json()}).then(setScenes).catch(()=>{if(!controller.signal.aborted)failure()});return()=>controller.abort()},[failure]);
 useEffect(()=>{
  const node=root.current;if(!node)return;
  const reduced=window.matchMedia("(prefers-reduced-motion: reduce)");
  let pending=0;
  const update=()=>{
   pending=0;
   const available=Math.max(1,document.documentElement.scrollHeight-window.innerHeight);
   node.style.setProperty("--page-scroll",String(reduced.matches?0:Math.min(window.scrollY,2500)));
   node.style.setProperty("--page-progress",String(Math.min(1,window.scrollY/available)));
  };
  const scroll=()=>{if(!pending)pending=requestAnimationFrame(update)};
  const pointer=(event:PointerEvent)=>{
   if(reduced.matches||event.pointerType==="touch")return;
   node.style.setProperty("--pointer-x",String((event.clientX/window.innerWidth-.5)*2));
   node.style.setProperty("--pointer-y",String((event.clientY/window.innerHeight-.5)*2));
  };
  update();window.addEventListener("scroll",scroll,{passive:true});window.addEventListener("resize",scroll);
  window.addEventListener("pointermove",pointer,{passive:true});
  return()=>{window.removeEventListener("scroll",scroll);window.removeEventListener("resize",scroll);window.removeEventListener("pointermove",pointer);if(pending)cancelAnimationFrame(pending)};
 },[]);
 return <div className="renaissance-backdrop" ref={root} aria-hidden="true" data-motion-status={status}>
  {SCENES.map((name,index)=><picture key={name}>{name==="hero"&&<source media="(max-width:760px)" srcSet="/renaissance/mobile-hero.jpg"/>}<img className={`scene ${index===Math.max(0,Math.min(scene,SCENES.length-1))?"active":""}`} src={`/renaissance/${name}.jpg`} alt="" draggable={false}/></picture>) }
  {scenes.length>0&&status!=='fallback'&&<CinemaCanvasBoundary onFailure={failure}><LiveCanvas scenes={scenes} active={Math.min(scene,scenes.length-1)} progress={0} opening={1} onStatus={handleStatus}/></CinemaCanvasBoundary>}
  <div className="renaissance-veil"/><div className="renaissance-grain"/>
  <div className="renaissance-progress"/>
 </div>;
}

export function RenaissanceIntro({onStart,canCreate}:{onStart:()=>void;canCreate:boolean}){
 return <section className="editor-workspace-intro"><span>VIDEO EDITOR WORKSPACE</span><h2>Không gian cho<br/>bản dựng tiếp theo.</h2><p>Chọn dự án, xem yêu cầu và chuẩn bị tư liệu cho công việc biên tập video của bạn.</p><button className="btn" onClick={onStart}>{canCreate?"Khởi tạo dự án":"Xem các dự án"}</button></section>;
}

export function RenaissanceJourney(){
 const track=useRef<HTMLDivElement>(null);
 useEffect(()=>{
  const node=track.current;if(!node)return;
  const reduced=window.matchMedia("(prefers-reduced-motion: reduce)");
  let frame=0;
  const update=()=>{
   frame=0;
   const bounds=node.getBoundingClientRect();
   const progress=Math.max(0,Math.min(1,-bounds.top/Math.max(1,bounds.height-window.innerHeight)));
   node.dataset.motion=reduced.matches?"reduced":"full";
   const position=progress*2;
   node.querySelectorAll<HTMLElement>(".renaissance-chapter").forEach((chapter,index)=>{
    const distance=index-position;
    const visibility=Math.max(0,1-Math.abs(distance));
    chapter.style.setProperty("--chapter-opacity",String(visibility));
    chapter.style.setProperty("--chapter-scale",String(1.22-Math.min(1,Math.abs(distance))*.18));
    chapter.style.setProperty("--chapter-shift",`${distance*95}px`);
    chapter.style.setProperty("--chapter-text",`${distance*140}px`);
    chapter.setAttribute("aria-hidden",String(visibility<.5));
   });
   node.style.setProperty("--film-progress",String(progress));
  };
  const schedule=()=>{if(!frame)frame=requestAnimationFrame(update)};
  update();window.addEventListener("scroll",schedule,{passive:true});window.addEventListener("resize",schedule);reduced.addEventListener("change",schedule);
  return()=>{window.removeEventListener("scroll",schedule);window.removeEventListener("resize",schedule);reduced.removeEventListener("change",schedule);if(frame)cancelAnimationFrame(frame)};
 },[]);
 const chapters=[
  {image:"assistant",number:"I",title:"Thu thập.",subtitle:"Một câu hỏi đúng. Một ý tưởng rõ hơn.",text:"Bắt đầu với mục tiêu, người xem và những thông tin cần truyền tải. Các câu hỏi chuyên sâu xuất hiện theo loại video của bạn."},
  {image:"gallery",number:"II",title:"Đối chiếu.",subtitle:"Giữ lại những gì làm nên dự án.",text:"Tài liệu gốc, câu trả lời và bằng chứng cùng nằm trong một hồ sơ. Thông tin còn thiếu hoặc mâu thuẫn được chỉ ra trước khi chuyển bước."},
  {image:"workshop",number:"III",title:"Xác nhận.",subtitle:"Cùng nhìn lại, trước khi đi tiếp.",text:"Người phụ trách xem hồ sơ, yêu cầu điều chỉnh và duyệt đúng phiên bản. Hồ sơ đã xác nhận có thể xuất thành PDF, Word và bộ tài liệu."}
 ];
 return <div ref={track} className="renaissance-journey" aria-label="Từ ý tưởng đến hồ sơ đã xác nhận"><div className="renaissance-film-stage"><div className="renaissance-film-guide">CUỘN ĐỂ CHUYỂN CẢNH <span>↓</span></div>{chapters.map(chapter=><section key={chapter.number} className="renaissance-chapter" style={{backgroundImage:`url(/renaissance/${chapter.image}.jpg)`}}>
  <div className="renaissance-chapter-inner"><span className="renaissance-eyebrow">THE PRODUCTION EDITION / {chapter.number}</span><h2>{chapter.title}</h2><p className="renaissance-chapter-subtitle">{chapter.subtitle}</p><p>{chapter.text}</p></div>
 </section>)}<div className="renaissance-film-progress"/></div></div>;
}
