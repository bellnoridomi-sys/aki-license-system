/* AKI Dev ambient effects — particles, cursor halo, reveal and micro-tilt */
(() => {
  "use strict";
  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const coarse = window.matchMedia("(pointer: coarse)").matches || window.innerWidth <= 760;
  const body = document.body;
  if (!body) return;

  body.classList.add("aki-page-ready", "aki-glass-control");
  const glassSelector = ".sidebar,.topbar,.navbar,.nav,.panel,.card,.stat-card,.feature-card,.key-card,.table-wrap,.table-container,.form-card,.content-card,.login-card,.dashboard-card,[class$='-panel'],[class$='-card'],.aki-v2-toolbar,.aki-v2-timeline,.aki-v2-command,.aki-v2-drawer";
  const glassNodes = Array.from(document.querySelectorAll(glassSelector))
    .filter((el) => !el.closest(".aki-global-backdrop") && !el.classList.contains("aki-v2-command-item"));
  glassNodes.forEach((el) => {
    el.classList.add("aki-glass-panel");
    if (el.matches(".sidebar,.navbar,.nav")) el.classList.add("aki-glass-sidebar", "aki-glass-nav");
    if (el.matches(".topbar")) el.classList.add("aki-glass-topbar");
    if (el.matches(".card,.stat-card,.feature-card,.key-card,.dashboard-card,[class$='-card']")) el.classList.add("aki-glass-interactive");
    if (!reduced && window.matchMedia("(hover:hover) and (pointer:fine)").matches) {
      let frame = 0;
      el.addEventListener("pointermove", (event) => {
        if (frame) return;
        frame = requestAnimationFrame(() => {
          const rect = el.getBoundingClientRect();
          const x = Math.max(0, Math.min(100, ((event.clientX - rect.left) / Math.max(rect.width, 1)) * 100));
          const y = Math.max(0, Math.min(100, ((event.clientY - rect.top) / Math.max(rect.height, 1)) * 100));
          el.style.setProperty("--aki-glass-x", x.toFixed(1) + "%");
          el.style.setProperty("--aki-glass-y", y.toFixed(1) + "%");
          frame = 0;
        });
      }, {passive:true});
      el.addEventListener("pointerleave", () => {
        el.style.setProperty("--aki-glass-x", "12%");
        el.style.setProperty("--aki-glass-y", "0%");
      }, {passive:true});
    }
  });
  const revealTargets = Array.from(document.querySelectorAll(".panel,.card,.stat-card,.table-wrap,.table-container,.feature-card,.key-card,.metric-card,.command-item,.login-gate"))
    .filter((el) => !el.closest("[hidden]") && !el.hasAttribute("hidden"));
  revealTargets.forEach((el, index) => {
    el.classList.add("aki-reveal");
    el.style.setProperty("--aki-delay", String((index % 6) * 55) + "ms");
    if (!coarse && !reduced && el.matches(".panel,.card,.stat-card,.feature-card,.key-card,.metric-card")) el.classList.add("aki-hover-card");
  });
  if (reduced || !("IntersectionObserver" in window)) revealTargets.forEach((el) => el.classList.add("aki-visible"));
  else {
    const observer = new IntersectionObserver((entries) => entries.forEach((entry) => {
      if (entry.isIntersecting) { entry.target.classList.add("aki-visible"); observer.unobserve(entry.target); }
    }), { threshold: .08, rootMargin: "0px 0px -36px 0px" });
    revealTargets.forEach((el) => observer.observe(el));
  }
  if (!coarse && !reduced && window.matchMedia("(hover:hover)").matches) {
    const glow = document.createElement("div");
    glow.className = "aki-cursor-glow"; glow.setAttribute("aria-hidden", "true"); body.appendChild(glow);
    let x = -300, y = -300, raf = 0;
    window.addEventListener("pointermove", (event) => {
      x = event.clientX; y = event.clientY;
      if (raf) return;
      raf = requestAnimationFrame(() => { glow.style.left = x + "px"; glow.style.top = y + "px"; raf = 0; });
    }, { passive: true });
  }
  const canvas = document.getElementById("aki-space");
  const ctx = canvas && canvas.getContext ? canvas.getContext("2d", { alpha: true }) : null;
  if (canvas && ctx && !coarse) {
    let width = 0, height = 0, dpr = 1, raf = 0, lastFrame = 0, visible = !document.hidden, wind = 0, particles = [];
    const seed = () => {
      const count = Math.min(90, Math.max(34, Math.round(width / 14)));
      particles = Array.from({ length: count }, () => ({x:Math.random()*width,y:Math.random()*height,depth:Math.random(),size:Math.random()*1.05+.25,alpha:Math.random()*.28+.06,phase:Math.random()*Math.PI*2}));
    };
    const resize = () => {
      width = window.innerWidth; height = window.innerHeight; dpr = Math.min(window.devicePixelRatio || 1, 1.5);
      canvas.width = Math.round(width*dpr); canvas.height = Math.round(height*dpr);
      canvas.style.width = width + "px"; canvas.style.height = height + "px"; ctx.setTransform(dpr,0,0,dpr,0,0); seed();
    };
    const draw = (time) => {
      if (!visible || document.hidden) return;
      if (!reduced && time-lastFrame<34) { raf=requestAnimationFrame(draw); return; }
      lastFrame=time; ctx.clearRect(0,0,width,height);
      const cx=width*.68,cy=height*.48,haze=ctx.createRadialGradient(cx,cy,4,cx,cy,Math.min(width,height)*.48);
      haze.addColorStop(0,"rgba(255,255,255,.028)"); haze.addColorStop(.48,"rgba(255,255,255,.009)"); haze.addColorStop(1,"rgba(255,255,255,0)");
      ctx.fillStyle=haze;ctx.fillRect(0,0,width,height);
      particles.forEach((p,i)=>{
        if(!reduced){p.y-=.12+p.depth*.34;p.x+=Math.sin(time*.00045+p.phase)*.08+wind*.008;}
        if(p.y<-8){p.y=height+8;p.x=Math.random()*width;}if(p.x<-8)p.x=width+8;if(p.x>width+8)p.x=-8;
        ctx.globalAlpha=p.alpha*(.55+p.depth*.45);ctx.fillStyle=i%19===0?"#fff":"#c9c9c4";
        ctx.beginPath();ctx.arc(p.x,p.y,.35+p.depth*p.size,0,Math.PI*2);ctx.fill();
      });
      ctx.globalAlpha=1;if(!reduced)raf=requestAnimationFrame(draw);
    };
    const start=()=>{cancelAnimationFrame(raf);if(visible&&!document.hidden)raf=requestAnimationFrame(draw);};
    resize();document.addEventListener("visibilitychange",()=>{visible=!document.hidden;if(visible)start();else cancelAnimationFrame(raf);});
    window.addEventListener("resize",()=>{resize();start();},{passive:true});
    if(!reduced&&window.matchMedia("(hover:hover)").matches)window.addEventListener("pointermove",(event)=>{wind=(event.clientX/Math.max(width,1)-.5)*2;},{passive:true});
    start();
  }
  if(!coarse&&!reduced)Array.from(document.querySelectorAll(".aki-uv-card,.u426-cd,.stat-card")).forEach((el)=>{
    el.classList.add("aki-tilt");
    el.addEventListener("pointermove",(event)=>{
      const r=el.getBoundingClientRect(),nx=(event.clientX-r.left)/Math.max(r.width,1)-.5,ny=(event.clientY-r.top)/Math.max(r.height,1)-.5;
      el.classList.add("aki-tilting");
      el.style.transform="perspective(900px) rotateX("+(ny*-3)+"deg) rotateY("+(nx*4)+"deg) translateY(-1px)";
    },{passive:true});
    el.addEventListener("pointerleave",()=>{el.classList.remove("aki-tilting");el.style.transform="";});
  });
})();