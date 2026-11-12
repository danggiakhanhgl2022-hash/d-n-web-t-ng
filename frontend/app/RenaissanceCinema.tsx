"use client";
import dynamic from "next/dynamic";
import {useCallback,useEffect,useRef,useState,type ReactNode,type CSSProperties} from "react";
import type {CinemaScene} from "./RenaissanceCanvas";
import {REFERENCE_SEQUENCE,INTRO_SECONDS,INTRO_SLOWDOWN} from "./referenceSequence";
import CinemaCanvasBoundary from "./CinemaCanvasBoundary";
const Canvas=dynamic(()=>import('./RenaissanceCanvas'),{ssr:false});
const CONTENT=[
 ['Video Editor.','Từ ý tưởng đến bản dựng.','Không gian làm việc dành cho editor video và người phụ trách sản xuất.'],
 ['Editor.','Hiểu câu chuyện trước khi dựng.','Video OS giúp editor tiếp nhận yêu cầu, làm rõ thông điệp và chuẩn bị hồ sơ trước khi mở phần mềm dựng phim.'],
 ['Ý tưởng.','Tìm hướng đi cho từng thước phim.','Xác định người xem, cảm xúc và mục tiêu để bản dựng có một hướng sáng tạo rõ ràng.'],
 ['Brief.','Nhận đúng yêu cầu từ đầu.','Thu thập nội dung, thời lượng, định dạng và yêu cầu hình ảnh bằng bộ câu hỏi theo loại video.'],
 ['Tư liệu.','Chuẩn bị chất liệu cho câu chuyện.','Tập hợp tài liệu tham chiếu và nguồn nội dung để editor hiểu bối cảnh của dự án.'],
 ['Phong cách.','Một ngôn ngữ hình ảnh nhất quán.','Làm rõ nhịp dựng, màu sắc, đồ họa và những video tham khảo trong brief sáng tạo.'],
 ['Âm thanh.','Đặt cảm xúc vào đúng nhịp.','Ghi nhận yêu cầu nhạc nền, lời đọc và âm thanh để chuẩn bị cho bước biên tập.'],
 ['Phiên bản.','Theo dõi từng lần điều chỉnh.','Giữ lịch sử thay đổi của hồ sơ yêu cầu để editor biết mình đang làm việc với phiên bản nào.'],
 ['Phản hồi.','Cùng hiểu một yêu cầu.','Người phụ trách kiểm tra hồ sơ, chỉ ra điểm chưa rõ và yêu cầu bổ sung trước khi sản xuất.'],
 ['Chốt brief.','Thống nhất trước khi bắt tay dựng.','Xác nhận và phê duyệt đúng phiên bản thông tin để giảm những lần phải sửa vì hiểu sai yêu cầu.'],
 ['Hồ sơ editor.','Mang theo đầy đủ thông tin cần thiết.','Xuất brief và hồ sơ đã được xác nhận thành PDF, Word hoặc bộ tài liệu để dùng trong quá trình dựng.'],
 ['Sẵn sàng dựng.','Một khởi đầu được chuẩn bị kỹ.','Tiếp tục công việc dựng phim trong phần mềm biên tập của bạn với yêu cầu và tư liệu đã được làm rõ.'],
 ['Cùng sáng tạo.','Bản dựng tiếp theo bắt đầu ở đây.','Đăng nhập để tiếp nhận dự án và chuẩn bị brief cho công việc biên tập video.']
];
const PAPER_TOPICS=[
 [['Mục tiêu','Video cần giúp người xem hiểu hoặc làm điều gì?'],['Người xem','Ghi rõ đối tượng và nơi video sẽ được sử dụng.'],['Đầu ra','Thời lượng, tỷ lệ khung hình và phiên bản cần bàn giao.']],
 [['Thông điệp','Chọn ý chính cần được giữ xuyên suốt bản dựng.'],['Tham chiếu','Tập hợp video, hình ảnh và tài liệu để cùng đối chiếu.'],['Cần làm rõ','Giữ lại những câu hỏi chưa có câu trả lời chắc chắn.']],
 [['Yêu cầu chung','Tách mục tiêu, nội dung và đầu ra thành từng câu rõ ràng.'],['Theo loại video','Điền thêm những câu phù hợp với dự án đang làm.'],['Xác nhận','Người phụ trách xem lại thông tin trước khi gửi duyệt.']],
 [['Tài liệu gốc','Giữ file được cung cấp cùng tên và nguồn của tài liệu.'],['Chứng cứ','Liên kết câu trả lời với phần thông tin chứng minh.'],['Đối chiếu','Đánh dấu khác biệt thay vì tự ghi đè yêu cầu cũ.']],
 [['Hình ảnh','Thống nhất màu sắc, bố cục và phong cách tham khảo.'],['Nhịp dựng','Làm rõ cảm xúc, tốc độ và cách kể câu chuyện.'],['Điều cần tránh','Ghi lại những lựa chọn không phù hợp với thương hiệu.']],
 [['Nhạc nền','Ghi thể loại, cảm xúc và bản nhạc tham chiếu.'],['Lời đọc','Chuẩn bị nội dung, ngôn ngữ và yêu cầu giọng đọc.'],['Âm thanh','Tập hợp các yêu cầu cần trao đổi với người dựng.']],
 [['Phiên bản hiện tại','Kiểm tra đúng thông tin đang được chỉnh sửa.'],['Lịch sử','Xem ai đã thay đổi và thay đổi phần nào.'],['Snapshot','Giữ nguyên hồ sơ tại thời điểm gửi xem xét.']],
 [['Góp ý cụ thể','Nêu phần cần sửa và lý do phải sửa.'],['Thông tin còn thiếu','Tách việc cần hỏi lại khỏi nội dung đã thống nhất.'],['Cùng xem lại','Người phụ trách xác nhận câu trả lời theo quyền của mình.']],
 [['Kiểm tra','Xử lý các mục bị chặn và thông tin còn mâu thuẫn.'],['Gửi duyệt','Tạo một phiên bản hồ sơ để người có quyền xem xét.'],['Quyết định','Ghi rõ duyệt, yêu cầu chỉnh sửa hoặc từ chối.']],
 [['Phiếu cho khách','Xuất bản thông tin dành cho khách hàng xem lại.'],['Hồ sơ đầy đủ','Tập hợp brief, chứng cứ và công việc còn mở.'],['Folder thông tin','Giữ các tài liệu và dữ liệu chuẩn hóa trong một bộ.']],
 [['Brief đã chốt','Kiểm tra phiên bản thông tin còn hiệu lực.'],['Tư liệu đi cùng','Mang theo đúng nguồn và tài liệu tham chiếu.'],['Bước tiếp theo','Dùng hồ sơ để tiếp tục trong phần mềm dựng của bạn.']],
 [['Mở không gian làm việc','Đăng nhập bằng tài khoản đã được cấp.'],['Chọn dự án','Tiếp tục hoàn thiện hoặc xem lại hồ sơ hiện có.'],['Bắt đầu rõ ràng','Chuẩn bị thông tin trước khi bắt tay vào bản dựng.']],
];
export default function RenaissanceCinema({onStart,opening,onOpeningComplete,autoLogin=true}:{onStart?:()=>void;opening?:ReactNode;onOpeningComplete?:()=>void;autoLogin?:boolean}){
 const loginDialog=useRef<HTMLDialogElement>(null);
 const [loginOpen,setLoginOpen]=useState(false);
 const enter=useCallback(()=>{if(onStart)onStart();else{loginTouched.current=true;setLoginOpen(true)}},[onStart]);
 useEffect(()=>{const dialog=loginDialog.current;if(!dialog)return;if(loginOpen&&!dialog.open)dialog.showModal();else if(!loginOpen&&dialog.open)dialog.close()},[loginOpen]);
 useEffect(()=>{if(location.hash==='#login-form')setLoginOpen(true)},[]);
 const root=useRef<HTMLDivElement>(null),started=useRef(0),paperNoise=useRef<SVGFETurbulenceElement>(null),fallbackLatched=useRef(false),autoLoginShown=useRef(false);const loginTouched=useRef(false);
 const [scenes,setScenes]=useState<CinemaScene[]>([]),[active,setActive]=useState(0),[progress,setProgress]=useState(0),[status,setStatus]=useState('loading');
 const [reduced,setReduced]=useState(false),[openingProgress,setOpeningProgress]=useState(0);
 useEffect(()=>{if(openingProgress>=1||status==='fallback')onOpeningComplete?.()},[openingProgress,status,onOpeningComplete]);
 // Wait for both the auth check and the rendered opening. Closing the dialog
 // must not immediately open it again during subsequent animation frames.
 useEffect(()=>{if(autoLogin&&!autoLoginShown.current&&(openingProgress>=.42||status==='fallback')){autoLoginShown.current=true;setLoginOpen(true)}},[autoLogin,openingProgress,status]);
 // Hộp đăng nhập tự hiện cùng khung hình, rồi tự tắt khi phần mở đầu chạy xong (trừ khi người dùng đã nhập/bấm vào hộp).
 useEffect(()=>{if(autoLogin&&autoLoginShown.current&&loginOpen&&!loginTouched.current&&active>=1)setLoginOpen(false)},[autoLogin,loginOpen,active]);
 // Giải mã sẵn ảnh nền của chương hiện tại và hai chương kế tiếp (giải mã ảnh lớn lúc chuyển chương gây khựng).
 const preloaded=useRef(new Set<string>());
 useEffect(()=>{
  [active,active+1,active+2].forEach(i=>{const src=scenes[i]?.fallback;if(!src||preloaded.current.has(src))return;preloaded.current.add(src);const img=new Image();img.src=src;img.decode?.().catch(()=>{})});
 },[scenes,active]);
 // Reloading a previously scrolled page must not start below the entrance.
 useEffect(()=>{const previous=history.scrollRestoration;history.scrollRestoration='manual';window.scrollTo({top:0,behavior:'instant'});return()=>{history.scrollRestoration=previous}},[]);
 const handleStatus=useCallback((next:string)=>{if(fallbackLatched.current&&next!=='fallback')return;if(next==='fallback')fallbackLatched.current=true;if((next==='ready'||next==='fallback')&&!started.current)started.current=performance.now();setStatus(next)},[]);
 const handleFailure=useCallback(()=>{const w=(window as unknown as {__cinemaWhy?:string});if(!w.__cinemaWhy)w.__cinemaWhy='timeout/boundary';handleStatus('fallback')},[handleStatus]);
 useEffect(()=>{let live=true;const controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),6000);fetch('/renaissance/3d/scenes.json',{signal:controller.signal}).then(r=>{if(!r.ok)throw Error('scenes');return r.json()}).then(data=>{if(live){if(!Array.isArray(data)||!data.length)throw Error('empty scenes');setScenes(data)}}).catch(e=>{if(live){(window as unknown as {__cinemaWhy?:string}).__cinemaWhy='scenes.json '+String(e).slice(0,60);handleStatus('fallback')}}).finally(()=>clearTimeout(timeout));return()=>{live=false;clearTimeout(timeout);controller.abort()}},[handleStatus]);
 // Compressed rigs can take longer on a cold browser than the manifest.
 // Do not permanently discard a working renderer after only six seconds.
 useEffect(()=>{if(status!=='loading')return;const timeout=setTimeout(handleFailure,20000);return()=>clearTimeout(timeout)},[status,handleFailure]);
 useEffect(()=>{
  const node=root.current;if(!node)return;const media=matchMedia('(prefers-reduced-motion: reduce)');
  const indexButtons=Array.from(node.querySelectorAll<HTMLButtonElement>('.cinema-index button'));
  let frame=0,lastNoise=0,lastScroll=NaN,lastHeight=0,lastWidth=0;
  const schedule=()=>{if(!frame&&!document.hidden)frame=requestAnimationFrame(update)};
  // Nội dung chương cố định: lấy phần tử một lần, mỗi khung hình chỉ ĐỌC hết rồi mới GHI để tránh ép trình duyệt tính lại bố cục liên tục (nguyên nhân gây đơ khi cuộn).
  const panels=Array.from(node.querySelectorAll<HTMLElement>('.cinema-chapter'));
  const spaceEls=panels.map(panel=>panel.querySelector<HTMLElement>('.cinema-scene-space'));
  const paperEls=panels.map(panel=>panel.querySelector<HTMLElement>('.cinema-paper'));
  const header=node.querySelector<HTMLElement>('.cinema-header');
  const last=CONTENT.length-1;
  const update=()=>{
   frame=0;
   const vh=innerHeight,isReduced=media.matches;
   // Opening still animates at rest, but its clock does not require layout reads.
   if(lastScroll===scrollY&&lastHeight===vh&&lastWidth===innerWidth){
    const arrival=started.current?Math.min(1,(performance.now()-started.current)/(INTRO_SECONDS*1000*INTRO_SLOWDOWN)):0;
    const opening=isReduced?1:arrival;
    setReduced(isReduced);setOpeningProgress(p=>(Math.abs(p-opening)<.02&&opening<1)?p:opening);
    node.style.setProperty('--opening',String(opening));
    if(started.current&&opening<1&&!isReduced)schedule();
    return;
   }
   lastScroll=scrollY;lastHeight=vh;lastWidth=innerWidth;
   // --- ĐỌC ---
   const rects=panels.map(panel=>panel.getBoundingClientRect());
   const spans=spaceEls.map(el=>el?.offsetHeight||vh);
   let index=0;
   for(let i=0;i<panels.length;i++)if(rects[i].top<=vh*.15)index=i;
   const bounds=rects[index];if(!bounds)return;
   const value=Math.max(0,Math.min(1,-bounds.top/Math.max(1,spans[index])));
   const arrival=started.current?Math.min(1,(performance.now()-started.current)/(INTRO_SECONDS*1000*INTRO_SLOWDOWN)):0;
   const opening=isReduced?1:arrival;
   const paper=paperEls[index]?.getBoundingClientRect();
   const inPaper=(y:number)=>index===last||!!paper&&paper.top<=y&&paper.bottom>=y;
   const buttonSurface=indexButtons.map(button=>{const box=button.getBoundingClientRect();return inPaper((box.top+box.bottom)*.5)?'light':'dark'});
   let headerSurface='dark';if(header){const box=header.getBoundingClientRect();headerSurface=inPaper((box.top+box.bottom)*.5)?'light':'dark'}
   const progresses=rects.map((box,i)=>Math.max(0,Math.min(1,-box.top/Math.max(1,spans[i]))));
   // --- GHI ---
   setReduced(isReduced);setActive(index);
   // Chỉ cập nhật React khi giá trị đổi đáng kể: tránh dựng lại toàn bộ trang ở mỗi khung hình.
   setProgress(p=>(Math.abs(p-value)<.015&&value>0&&value<1)?p:value);
   setOpeningProgress(p=>(Math.abs(p-opening)<.02&&opening<1)?p:opening);
   node.style.setProperty('--opening',String(opening));
   node.dataset.paper=String(index===last||!!paper&&paper.top<vh*.5&&paper.bottom>vh*.5);
   indexButtons.forEach((button,k)=>{if(button.dataset.surface!==buttonSurface[k])button.dataset.surface=buttonSurface[k]});
   if(header&&header.dataset.surface!==headerSurface)header.dataset.surface=headerSurface;
   panels.forEach((panel,i)=>{const next=String(progresses[i]);if(panel.style.getPropertyValue('--chapter-progress')!==next)panel.style.setProperty('--chapter-progress',next);const flag=String(i===index);if(panel.dataset.active!==flag)panel.dataset.active=flag});
   if(started.current&&opening<1&&!isReduced)schedule();
  };
  window.addEventListener('scroll',schedule,{passive:true});window.addEventListener('resize',schedule);document.addEventListener('visibilitychange',schedule);media.addEventListener('change',schedule);
  const resize=new ResizeObserver(schedule);resize.observe(node);
  schedule();return()=>{cancelAnimationFrame(frame);resize.disconnect();window.removeEventListener('scroll',schedule);window.removeEventListener('resize',schedule);document.removeEventListener('visibilitychange',schedule);media.removeEventListener('change',schedule)};
 },[scenes,status]);
 const jump=(index:number)=>root.current?.querySelectorAll('.cinema-chapter')[index]?.scrollIntoView({behavior:reduced?'instant':'smooth'});
 return <div ref={root} className="renaissance-cinema" data-chapter={active} data-status={status} data-reduced={reduced} data-arrived={reduced||openingProgress>=.42||status==='fallback'} data-intro-done={reduced||openingProgress>=1||status==='fallback'}>
  <svg aria-hidden="true" focusable="false" width="0" height="0" style={{position:'absolute'}}><defs><filter id="cinema-paper-edge" x="-10%" y="-70%" width="120%" height="240%"><feTurbulence ref={paperNoise} type="fractalNoise" baseFrequency=".009 .04" numOctaves="3" seed="5" stitchTiles="stitch" result="paper-noise"/><feDisplacementMap in="SourceGraphic" in2="paper-noise" scale="28" xChannelSelector="R" yChannelSelector="G"/></filter></defs></svg>
  <header className="cinema-header"><a href="#cinema-opening" className="cinema-wordmark">videoOS <span>Production Edition</span></a><a className="cinema-enter" href="#login-form" onClick={e=>{e.preventDefault();enter()}}>Vào dự án <span>↗</span></a></header>
  <div className="cinema-visual"><div className="cinema-fallback" style={{backgroundImage:`url(${scenes[active]?.fallback||'/renaissance/hero.jpg'})`}}/>{scenes.length>0&&status!=='fallback'&&<CinemaCanvasBoundary onFailure={handleFailure}><Canvas scenes={scenes} active={active} progress={progress} opening={openingProgress} onStatus={handleStatus}/></CinemaCanvasBoundary>}<div className="cinema-shade"/><div className="cinema-opening-emblem" aria-hidden="true" hidden><span>videoOS</span><strong>Production<br/>Edition.</strong><small>Một khởi đầu cho<br/>mọi câu chuyện.</small></div></div>
  <nav className="cinema-index" aria-label="Các chương trải nghiệm">{CONTENT.map((content,index)=><button key={content[0]} type="button" onClick={()=>jump(index)} aria-current={active===index?'step':undefined}><span>{content[0]}</span><small>{String(index).padStart(2,'0')}</small></button>)}</nav>
  {CONTENT.map((content,index)=><section className={`cinema-chapter ${index===0?'cinema-opening':''}`} id={index===0?'cinema-opening':`cinema-${index}`} key={content[0]} aria-label={content[0]} data-reference-start={REFERENCE_SEQUENCE[index].start} data-reference-end={REFERENCE_SEQUENCE[index].end} style={{'--scene-travel':`${REFERENCE_SEQUENCE[index].travel}svh`} as CSSProperties}>
   <div className="cinema-sticky"><div className="cinema-copy">{index===0?(<div className="cinema-cover"><h1>The<br/><em>Production</em><br/>Edition.</h1><p>Một khởi đầu cho<br/>mọi câu chuyện.</p><div className="cinema-cover-list">{CONTENT.slice(1,9).map((row,i)=><button key={row[0]} onClick={()=>jump(i+1)}>{row[0]}<span>{['I','II','III','IV','V','VI','VII','VIII'][i]}</span></button>)}</div></div>):<><span className="cinema-kicker">VIDEO OS / {String(index).padStart(2,'0')}</span><h2>{content[0]}</h2><p>{content[1]}</p></> }</div><div className="cinema-scroll">CUỘN XUỐNG · KHÁM PHÁ KHÔNG GIAN CHO EDITOR <span>↓</span></div></div>
   <div className="cinema-scene-space" aria-hidden="true"/>
   {index>0&&<div className="cinema-paper"><span>{String(index).padStart(2,'0')} / THE PRODUCTION EDITION</span><h3>{content[1]}</h3><p>{content[2]}</p><figure className="cinema-paper-showcase"><div className="cinema-showcase-art">{scenes[index]?.fallback&&<img src={scenes[index].fallback} alt="" width={720} height={420} loading="lazy" decoding="async"/>}</div><div className="cinema-document-preview" aria-hidden="true"><span className="cinema-preview-bar"><i/><i/><i/></span><small>HỒ SƠ DỰ ÁN · MINH HỌA</small><strong>{content[0]}</strong>{PAPER_TOPICS[index-1].map(([title])=><div className="cinema-preview-row" key={title}><span>{title}</span><i/></div>)}</div></figure><div className="cinema-feature-grid">{PAPER_TOPICS[index-1].map(([title,text],i)=><article className="cinema-feature" key={title}><span>{String(i+1).padStart(2,'0')}</span><h4>{title}</h4><p>{text}</p></article>)}</div>{index===CONTENT.length-1&&<a className="cinema-paper-enter" href="#login-form" onClick={e=>{e.preventDefault();enter()}}>Vào không gian làm việc ↗</a>}</div>}
  </section>)}
  <dialog ref={loginDialog} className="cinema-login-dialog" onKeyDownCapture={()=>{loginTouched.current=true}} onPointerDownCapture={()=>{loginTouched.current=true}} onCancel={()=>setLoginOpen(false)} onClick={e=>{if(e.target===e.currentTarget)setLoginOpen(false)}}><button type="button" className="cinema-dialog-close" onClick={()=>setLoginOpen(false)} aria-label="Đóng đăng nhập">×</button>{opening}</dialog><span className="cinema-render-status" role="status">{status==='loading'?'Đang chuẩn bị cảnh mở… '+((window as unknown as {__cinemaTrace?:string[]}).__cinemaTrace||[]).slice(-4).join(' '):status==='fallback'?'Cảnh đang dùng ảnh dự phòng '+((window as unknown as {__cinemaTrace?:string[]}).__cinemaTrace||[]).slice(-5).join(' ')+((window as unknown as {__cinemaWhy?:string}).__cinemaWhy?' ['+(window as unknown as {__cinemaWhy?:string}).__cinemaWhy+']':''):''}</span>
 </div>;
}
