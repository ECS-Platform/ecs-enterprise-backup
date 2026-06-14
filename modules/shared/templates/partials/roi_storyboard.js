{# ROI Executive Storyboard — vanilla JS state machine.
   Count-up animations, autoplay, manual step, keyboard nav, fullscreen,
   presentation mode, projected/actual toggle. No external libraries. #}
<script>
(function(){
  "use strict";
  var root = document.querySelector('[data-roi-root]');
  if(!root) return;
  var DATA = window.ECS_ROI || {};
  var cur = (DATA.currency && DATA.currency.symbol) || '\u20b9';
  var stage = root.querySelector('[data-roi-stage]');
  if(!stage) return;
  var screens = Array.prototype.slice.call(stage.querySelectorAll('[data-roi-screen]'));
  var idx = 0, playing = true, timer = null;
  var AUTO_MS = 6500;

  /* ---------- INR formatting (mirrors server format_inr) ---------- */
  var LAKH = 100000, CRORE = 10000000;
  function fmtINR(n){
    n = Number(n)||0; var sign = n<0?'-':''; n = Math.abs(n);
    if(n>=CRORE) return sign+cur+trim(n/CRORE)+' Cr';
    if(n>=LAKH) return sign+cur+trim(n/LAKH)+' Lakh';
    return sign+cur+Math.round(n).toLocaleString('en-IN');
  }
  function trim(x){ return (Math.round(x*100)/100).toString(); }
  function fmtNum(n){ return Math.round(Number(n)||0).toLocaleString('en-IN'); }

  /* ---------- count-up ---------- */
  function animateValue(el){
    var isMoney = el.hasAttribute('data-money');
    var target = Number(el.getAttribute(isMoney?'data-money':'data-count'))||0;
    var suffix = el.getAttribute('data-suffix')||'';
    var dur = 1100, start = performance.now();
    var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if(reduce){ el.textContent = isMoney?fmtINR(target):(fmtNum(target)+suffix); return; }
    function step(now){
      var t = Math.min(1,(now-start)/dur);
      var eased = 1-Math.pow(1-t,3);
      var v = target*eased;
      el.textContent = isMoney?fmtINR(v):(fmtNum(v)+suffix);
      if(t<1) requestAnimationFrame(step);
      else el.textContent = isMoney?fmtINR(target):(fmtNum(target)+suffix);
    }
    requestAnimationFrame(step);
  }
  function runCounters(screen){
    screen.querySelectorAll('[data-count],[data-money]').forEach(function(el){
      el.__done=false; animateValue(el);
    });
  }

  /* ---------- screen control ---------- */
  function show(i){
    if(i<0) i=screens.length-1; if(i>=screens.length) i=0;
    idx=i;
    screens.forEach(function(s,k){ s.classList.toggle('is-active', k===idx); });
    var active = screens[idx];
    if(active) runCounters(active);
    updateDots();
  }
  function next(){ show(idx+1); }
  function prev(){ show(idx-1); }

  /* ---------- dots ---------- */
  var dotsWrap = root.querySelector('[data-roi-dots]');
  function buildDots(){
    if(!dotsWrap) return;
    dotsWrap.innerHTML='';
    screens.forEach(function(s,k){
      var d=document.createElement('span'); d.className='roi-dot';
      d.title = s.getAttribute('data-roi-title')||('Screen '+(k+1));
      d.addEventListener('click',function(){ show(k); restart(); });
      dotsWrap.appendChild(d);
    });
  }
  function updateDots(){
    if(!dotsWrap) return;
    Array.prototype.forEach.call(dotsWrap.children,function(d,k){
      d.classList.toggle('is-active',k===idx);
    });
  }

  /* ---------- autoplay ---------- */
  function tick(){ if(playing) next(); }
  function start(){ stop(); timer=setInterval(tick,AUTO_MS); }
  function stop(){ if(timer){ clearInterval(timer); timer=null; } }
  function restart(){ if(playing) start(); }
  var playBtn = root.querySelector('[data-roi-play]');
  function setPlaying(p){
    playing=p;
    if(playBtn) playBtn.textContent = p?'\u23f8 Pause':'\u25b6 Play';
    if(p) start(); else stop();
  }

  /* ---------- presentation + fullscreen ---------- */
  var main = root;
  var exitBtn = root.querySelector('[data-roi-exit]');
  function enterPresent(){
    main.classList.add('is-presenting');
    if(exitBtn) exitBtn.hidden=false;
    requestFS(main);
    setPlaying(true);
    show(0);
  }
  function exitPresent(){
    main.classList.remove('is-presenting');
    if(exitBtn) exitBtn.hidden=true;
    exitFS();
  }
  function requestFS(el){
    var fn = el.requestFullscreen||el.webkitRequestFullscreen||el.msRequestFullscreen;
    if(fn){ try{ fn.call(el); }catch(e){} }
  }
  function exitFS(){
    if(document.fullscreenElement||document.webkitFullscreenElement){
      var fn = document.exitFullscreen||document.webkitExitFullscreen;
      if(fn){ try{ fn.call(document); }catch(e){} }
    }
  }
  document.addEventListener('fullscreenchange',function(){
    if(!document.fullscreenElement){ main.classList.remove('is-presenting'); if(exitBtn) exitBtn.hidden=true; }
  });

  /* ---------- mode toggle (projected/actual) ---------- */
  var toggle = root.querySelector('[data-roi-mode-toggle]');
  if(toggle){
    toggle.addEventListener('click',function(e){
      var btn = e.target.closest('[data-roi-mode]'); if(!btn) return;
      toggle.querySelectorAll('.roi-toggle-btn').forEach(function(b){ b.classList.remove('is-active'); });
      btn.classList.add('is-active');
      applyMode(btn.getAttribute('data-roi-mode'));
    });
  }
  function applyMode(mode){
    var sc = DATA.scenario||{};
    var res = (mode==='actual'?sc.actual:sc.projected)||{};
    // Update the variance screen headline values + any [data-roi-mode-cost] sinks.
    root.querySelectorAll('[data-roi-mode-cost]').forEach(function(el){
      el.textContent = fmtINR(res.cost_savings||0);
    });
    root.setAttribute('data-roi-active-mode',mode);
    // Re-run counters on the visible screen to reflect mode.
    if(screens[idx]) runCounters(screens[idx]);
  }

  /* ---------- wire buttons ---------- */
  bind('[data-roi-next]',function(){ next(); restart(); });
  bind('[data-roi-prev]',function(){ prev(); restart(); });
  bind('[data-roi-play]',function(){ setPlaying(!playing); });
  bind('[data-roi-fullscreen]',function(){ requestFS(main); });
  bind('[data-roi-present]',enterPresent);
  bind('[data-roi-exit]',exitPresent);
  function bind(sel,fn){ var el=root.querySelector(sel); if(el) el.addEventListener('click',fn); }

  /* ---------- keyboard ---------- */
  document.addEventListener('keydown',function(e){
    if(e.key==='ArrowRight'){ next(); restart(); }
    else if(e.key==='ArrowLeft'){ prev(); restart(); }
    else if(e.key===' '){ e.preventDefault(); setPlaying(!playing); }
    else if(e.key==='Escape'){ exitPresent(); }
    else if(e.key==='f'||e.key==='F'){ requestFS(main); }
  });

  /* ---------- enterprise rollout simulator ---------- */
  (function(){
    var sim = root.querySelector('[data-roi-sim]');
    if(!sim) return;
    var slider = sim.querySelector('[data-roi-sim-slider]');
    var pts = (DATA.rollout_simulator && DATA.rollout_simulator.points) || [];
    if(!slider || !pts.length) return;
    var appsEl = sim.querySelector('[data-roi-sim-apps]');
    function fmtMetric(el,p){
      var key = el.getAttribute('data-roi-sim-metric');
      var suffix = el.getAttribute('data-suffix')||'';
      var isMoney = el.hasAttribute('data-money');
      var v = p[key];
      if(isMoney){ el.textContent = (p.cost_savings_display!=null? p.cost_savings_display : fmtINR(v)); }
      else if(key==='fte_equivalent'){ el.textContent = (Math.round(v*100)/100)+suffix; }
      else if(key==='roi_pct'){ el.textContent = v+suffix; }
      else { el.textContent = fmtNum(v)+suffix; }
    }
    function apply(i){
      i = Math.max(0,Math.min(pts.length-1,i|0));
      var p = pts[i];
      if(appsEl) appsEl.textContent = fmtNum(p.applications);
      sim.querySelectorAll('[data-roi-sim-metric]').forEach(function(el){
        fmtMetric(el,p);
        el.classList.remove('is-bumped'); void el.offsetWidth; el.classList.add('is-bumped');
      });
    }
    slider.addEventListener('input',function(){ apply(Number(slider.value)); });
    apply(Number(slider.value)||0);
  })();

  /* ---------- init ---------- */
  buildDots();
  setPlaying(true);
  show(0);
})();
</script>
