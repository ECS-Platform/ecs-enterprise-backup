{# ROI Executive Storyboard — vanilla JS state machine.
   Count-up animations, autoplay, manual step, keyboard nav, fullscreen,
   presentation mode, projected/actual toggle. No external libraries. #}
<script>
(function(){
  "use strict";
  var root = document.querySelector('[data-roi-root]');
  if(!root) return;
  var DATA = window.ECS_ROI || {};
  // `view` is the active scenario's payload. Top-level DATA already equals the
  // active scenario (server emits it flat for back-compat) but we re-point it to
  // DATA.scenarios[name] on toggle so every recompute is fully deterministic.
  var view = DATA;
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
    var sc = view.scenario||{};
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
  var simApply = null;
  (function(){
    var sim = root.querySelector('[data-roi-sim]');
    if(!sim) return;
    var slider = sim.querySelector('[data-roi-sim-slider]');
    if(!slider) return;
    var appsEl = sim.querySelector('[data-roi-sim-apps]');
    function pts(){ return (view.rollout_simulator && view.rollout_simulator.points) || []; }
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
    simApply = function(i){
      var P = pts(); if(!P.length) return;
      if(i==null) i = Number(slider.value)||0;
      i = Math.max(0,Math.min(P.length-1,i|0));
      var p = P[i];
      if(appsEl) appsEl.textContent = fmtNum(p.applications);
      sim.querySelectorAll('[data-roi-sim-metric]').forEach(function(el){
        fmtMetric(el,p);
        el.classList.remove('is-bumped'); void el.offsetWidth; el.classList.add('is-bumped');
      });
    };
    slider.addEventListener('input',function(){ simApply(Number(slider.value)); });
    simApply(Number(slider.value)||0);
  })();

  /* ---------- scenario toggle (recomputes everything) ---------- */
  function getPath(obj,path){
    return path.split('.').reduce(function(o,k){ return (o==null)?undefined:o[k]; }, obj);
  }
  function applyBinds(){
    root.querySelectorAll('[data-roi-bind]').forEach(function(el){
      var v = getPath(view, el.getAttribute('data-roi-bind'));
      if(v===undefined||v===null) return;
      var fmt = el.getAttribute('data-roi-bind-fmt');
      if(fmt==='money'){
        // keep count-up: update data-money so counters animate to new target
        el.setAttribute('data-money', v);
      } else if(el.hasAttribute('data-count')){
        el.setAttribute('data-count', v);
      } else {
        el.textContent = (typeof v==='number') ? fmtNum(v) : v;
      }
    });
  }
  function el(tag,cls,html){ var e=document.createElement(tag); if(cls)e.className=cls; if(html!=null)e.innerHTML=html; return e; }
  function renderRegion(name){
    var host = root.querySelector('[data-roi-region="'+name+'"]'); if(!host) return;
    if(name==='takeaways'){
      var cards=(view.executive_takeaways&&view.executive_takeaways.cards)||[]; host.innerHTML='';
      cards.forEach(function(t,k){ host.appendChild(el('div','roi-takeaway-card',
        '<div class="roi-takeaway-title">'+t.title+'</div><div class="roi-takeaway-value">'+t.value+'</div><div class="roi-takeaway-sub">'+t.sub+'</div>')); });
    } else if(name==='drivers'){
      var ds=(view.value_drivers&&view.value_drivers.drivers)||[]; host.innerHTML='';
      ds.forEach(function(d){ var tr=d.trend==='up'?'▲':(d.trend==='down'?'▼':'—');
        host.appendChild(el('div','roi-driver-card',
        '<div class="roi-driver-top"><span class="roi-driver-name">'+d.name+'</span><span class="roi-driver-trend roi-trend-'+d.trend+'">'+tr+'</span></div>'+
        '<div class="roi-driver-bar"><span class="roi-driver-fill" style="--w:'+d.contribution_pct+'%"></span></div>'+
        '<div class="roi-driver-pct">'+d.contribution_pct+'%</div>'+
        '<ul class="roi-driver-stats"><li><span>Hours saved</span><b>'+fmtNum(d.hours_saved)+'</b></li>'+
        '<li class="roi-detail-money"><span>Cost saved</span><b>'+d.cost_saved_display+'</b></li></ul>')); });
    } else if(name==='payback'){
      var pb=view.payback||{}; host.innerHTML='';
      host.appendChild(el('div','roi-payback-card','<div class="roi-payback-lbl">Investment Cost</div><div class="roi-payback-val">'+pb.investment_display+'</div>'));
      host.appendChild(el('div','roi-payback-card','<div class="roi-payback-lbl">Annual Savings</div><div class="roi-payback-val">'+pb.annual_savings_display+'</div>'));
      host.appendChild(el('div','roi-payback-card roi-payback-hero','<div class="roi-payback-lbl">Payback Period</div><div class="roi-payback-val">'+pb.payback_months+' <small>months</small></div>'));
      (pb.horizons||[]).forEach(function(h){ host.appendChild(el('div','roi-payback-card','<div class="roi-payback-lbl">'+h.years+'-Year Net Value</div><div class="roi-payback-val">'+h.net_value_display+'</div>')); });
    } else if(name==='ranking'){
      var rk=(view.framework_ranking||[]).slice(0,3); host.innerHTML='';
      rk.forEach(function(r){ host.appendChild(el('div','roi-rank-card'+(r.is_top?' roi-rank-top':''),
        '<div class="roi-rank-badge">#'+r.rank+'</div><div class="roi-rank-name">'+r.name+'</div>'+
        '<div class="roi-rank-cost">'+r.cost_saved_display+'</div>'+
        '<div class="roi-rank-sub">'+r.roi_contribution_pct+'% of framework value'+(r.is_top?' · Highest value framework':'')+'</div>')); });
    } else if(name==='fw-table'){
      var fws=view.framework_roi||[]; host.innerHTML='';
      fws.forEach(function(f){ host.appendChild(el('tr',null,
        '<td class="roi-fw-td-name">'+f.name+'</td><td>'+f.applications_covered+'</td><td>'+f.observations_closed+'</td>'+
        '<td>'+f.evidence_reused+'</td><td>'+fmtNum(f.emails_avoided)+'</td><td>'+fmtNum(f.hours_saved)+'</td>'+
        '<td class="roi-fw-td-money">'+f.cost_saved_display+'</td><td>'+f.roi_pct+'%</td>'+
        '<td><div class="roi-fw-contrib"><span class="roi-fw-contrib-fill" style="--w:'+f.roi_contribution_pct+'%"></span></div>'+
        '<span class="roi-fw-contrib-num">'+f.roi_contribution_pct+'%</span></td>')); });
    } else if(name==='waterfall'){
      var wf=view.waterfall||{}; var steps=wf.steps||[]; var wmax=wf.total||1; host.innerHTML='';
      steps.forEach(function(s,k){ var col=el('div','roi-wf-col'+(s.is_total?' roi-wf-total':''));
        col.innerHTML='<div class="roi-wf-bar" style="--h:'+Math.round((s.value/wmax)*100)+'%; --d:'+(k*0.12)+'s" title="'+s.label+': '+s.value_display+'">'+
        '<span class="roi-wf-val">'+s.value_display+'</span></div>'+
        '<div class="roi-wf-x">'+s.label+(s.is_total?'':'<br><small>'+s.pct_of_total+'%</small>')+'</div>';
        host.appendChild(col); });
    } else if(name==='invest-summary'){
      var iv=view.investment_view||{}; host.innerHTML=
        '<div class="roi-invest-pill"><span>Total Investment</span><b>'+iv.total_investment_display+'</b></div>'+
        '<div class="roi-invest-pill"><span>Headcount</span><b>'+iv.total_headcount+'</b></div>'+
        '<div class="roi-invest-pill roi-invest-pill-hero"><span>Value Generated</span><b>'+iv.value_generated_display+'</b></div>'+
        '<div class="roi-invest-pill roi-invest-pill-mult"><span>Return Multiple</span><b>'+iv.value_multiple+'×</b></div>';
    } else if(name==='invest-table'){
      var ws=(view.investment_view&&view.investment_view.workstreams)||[];
      var tb=host.querySelector('tbody')||host; tb.innerHTML='';
      ws.forEach(function(w){ tb.appendChild(el('tr',null,'<td class="roi-fw-td-name">'+w.name+'</td><td>'+w.headcount+'</td><td class="roi-fw-td-money">'+w.annual_cost_display+'</td>')); });
    }
  }
  function applyScenario(name){
    var scn = DATA.scenarios && DATA.scenarios[name];
    if(!scn) return;
    view = scn;
    cur = (view.currency && view.currency.symbol) || cur;
    // header binds + all bound headline metrics
    applyBinds();
    // dynamic regions
    ['takeaways','drivers','payback','ranking','fw-table','waterfall','invest-summary','invest-table'].forEach(renderRegion);
    // re-run counters on the visible storyboard screen
    if(screens[idx]) runCounters(screens[idx]);
    // refresh rollout simulator against the new scenario
    if(simApply) simApply(null);
    root.setAttribute('data-roi-scenario', name);
  }
  var scenarioBar = root.querySelector('[data-roi-scenario-bar]');
  if(scenarioBar){
    scenarioBar.addEventListener('click',function(e){
      var btn=e.target.closest('[data-roi-scenario]'); if(!btn) return;
      scenarioBar.querySelectorAll('.roi-scenario-btn').forEach(function(b){ b.classList.remove('is-active'); b.setAttribute('aria-selected','false'); });
      btn.classList.add('is-active'); btn.setAttribute('aria-selected','true');
      applyScenario(btn.getAttribute('data-roi-scenario'));
    });
  }

  /* ---------- boardroom deck (3 slides, manual nav, NO autoplay) ---------- */
  (function(){
    var deck = root.querySelector('[data-roi-deck]');
    if(!deck) return;
    var slides = Array.prototype.slice.call(deck.querySelectorAll('[data-deck-slide]'));
    if(!slides.length) return;
    var di = 0;
    var dotsWrap = deck.querySelector('[data-deck-dots]');
    var curEl = deck.querySelector('[data-deck-current]');

    function buildDeckDots(){
      if(!dotsWrap) return; dotsWrap.innerHTML='';
      slides.forEach(function(s,k){
        var d=document.createElement('span'); d.className='roi-deck-dot';
        d.title=s.getAttribute('data-deck-title')||('Slide '+(k+1));
        d.addEventListener('click',function(){ showDeck(k); });
        dotsWrap.appendChild(d);
      });
    }
    function updateDeckDots(){
      if(dotsWrap) Array.prototype.forEach.call(dotsWrap.children,function(d,k){ d.classList.toggle('is-active',k===di); });
      if(curEl) curEl.textContent = (di+1);
    }
    function showDeck(i){
      if(i<0) i=0; if(i>=slides.length) i=slides.length-1;
      di=i;
      slides.forEach(function(s,k){ s.classList.toggle('is-active',k===di); });
      updateDeckDots();
    }
    function deckNext(){ showDeck(di+1); }
    function deckPrev(){ showDeck(di-1); }
    function db(sel,fn){ var el=deck.querySelector(sel); if(el) el.addEventListener('click',fn); }
    db('[data-deck-next]',deckNext);
    db('[data-deck-prev]',deckPrev);

    // presentation mode (fills viewport; manual only)
    var exitBtn=deck.querySelector('[data-deck-exit]');
    function enterPresent(){ deck.classList.add('is-presenting'); if(exitBtn) exitBtn.hidden=false;
      var fn=deck.requestFullscreen||deck.webkitRequestFullscreen; if(fn){try{fn.call(deck);}catch(e){}} }
    function exitPresent(){ deck.classList.remove('is-presenting'); if(exitBtn) exitBtn.hidden=true;
      if(document.fullscreenElement){var fn=document.exitFullscreen||document.webkitExitFullscreen; if(fn){try{fn.call(document);}catch(e){}}} }
    db('[data-deck-present]',enterPresent);
    db('[data-deck-exit]',exitPresent);
    document.addEventListener('fullscreenchange',function(){ if(!document.fullscreenElement){ deck.classList.remove('is-presenting'); if(exitBtn) exitBtn.hidden=true; } });

    // keyboard (only when deck is the focus / presenting)
    document.addEventListener('keydown',function(e){
      var presenting = deck.classList.contains('is-presenting');
      if(!presenting && !isDeckInView()) return;
      if(e.key==='ArrowRight'){ e.preventDefault(); deckNext(); }
      else if(e.key==='ArrowLeft'){ e.preventDefault(); deckPrev(); }
      else if(e.key==='Escape'){ exitPresent(); }
    });
    function isDeckInView(){
      var r=deck.getBoundingClientRect();
      return r.top < window.innerHeight && r.bottom > 0;
    }

    // appendix toggle
    var appendix = root.querySelector('[data-roi-appendix]');
    var appBtn = deck.querySelector('[data-deck-appendix]');
    if(appBtn && appendix){
      appBtn.addEventListener('click',function(){
        var hidden = appendix.hasAttribute('hidden');
        if(hidden){ appendix.removeAttribute('hidden'); appBtn.textContent='Appendix / Details ▴'; appendix.scrollIntoView({behavior:'smooth'}); }
        else { appendix.setAttribute('hidden',''); appBtn.textContent='Appendix / Details ▾'; }
      });
    }

    // scenario toggle re-renders the Executive Value Dashboard (slide 3).
    // Slides 1 (Framework) & 2 (FTE) are fixed/scenario-independent.
    function applyDeckScenario(name){
      var scn = DATA.scenarios && DATA.scenarios[name];
      var d = scn ? scn.deck : (DATA.deck||{});
      if(!d || !d.rows) return;
      var rows = d.rows;
      // dashboard 5-year table
      var dash = deck.querySelector('.roi-dash-table tbody');
      if(dash){
        function rowHTML(label, getter, cls){
          var h='<td>'+label+'</td>';
          rows.forEach(function(r){ h+='<td class="num'+(cls?(' '+cls):'')+'">'+getter(r)+'</td>'; });
          return h;
        }
        dash.innerHTML='';
        var defs=[
          ['Applications',function(r){return r.applications;},''],
          ['Annual Savings (Cr)',function(r){return r.annual_savings_cr;},''],
          ['Cumulative Savings (Cr)',function(r){return r.cumulative_savings_cr;},''],
          ['ECS Cost (Cr)',function(r){return r.ecs_cost_cr;},''],
          ['Cumulative Cost (Cr)',function(r){return r.cumulative_cost_cr;},''],
          ['Net Benefit (Cr)',function(r){return r.net_benefit_cr;},'roi-cell-gold'],
          ['Payback Status',function(){return 'Achieved';},'roi-cell-ok']
        ];
        defs.forEach(function(dd){ var tr=document.createElement('tr'); tr.innerHTML=rowHTML(dd[0],dd[1],dd[2]); dash.appendChild(tr); });
        // refresh dashboard header (year columns are stable but rebuild defensively)
        var head = deck.querySelector('.roi-dash-table thead tr');
        if(head){ var hh='<th>Metric</th>'; rows.forEach(function(r){ hh+='<th class="num">Year '+r.year+'</th>'; }); head.innerHTML=hh; }
      }
      // dashboard net-benefit bar chart
      var chartEl = deck.querySelector('.roi-dash-chart .roi-chart');
      if(chartEl && d.chart){
        var c=d.chart, maxn=c.max_net||1;
        chartEl.innerHTML='';
        c.labels.forEach(function(lab,k){
          var col=document.createElement('div'); col.className='roi-bar-col';
          var pct=Math.round(c.net[k]/maxn*1000)/10;
          col.innerHTML='<div class="roi-bar-val">'+c.net[k]+'</div>'+
            '<div class="roi-bar-track"><div class="roi-bar-fill" style="height:'+pct+'%"></div></div>'+
            '<div class="roi-bar-x">'+lab+'</div>';
          chartEl.appendChild(col);
        });
      }
      // dashboard callout banner
      var last = rows[rows.length-1];
      var cApps = deck.querySelector('.roi-dash-callout .roi-callout-item:nth-child(1) b');
      var cNet  = deck.querySelector('.roi-dash-callout .roi-callout-gold b');
      var cOpex = deck.querySelector('.roi-dash-callout .roi-callout-item:nth-child(4) b');
      if(cApps) cApps.textContent = last.applications;
      if(cNet)  cNet.textContent  = last.net_benefit_display;
      if(cOpex) cOpex.textContent = d.steady_cost_display||cOpex.textContent;
    }
    var sbar = root.querySelector('[data-roi-scenario-bar]');
    if(sbar){ sbar.addEventListener('click',function(e){ var b=e.target.closest('[data-roi-scenario]'); if(b) applyDeckScenario(b.getAttribute('data-roi-scenario')); }); }

    buildDeckDots();
    // optional deep-link: #slide=N opens slide N directly (presenter convenience)
    var m = /[#&]slide=(\d+)/.exec(window.location.hash||'');
    showDeck(m ? (parseInt(m[1],10)-1) : 0);   // manual; no autoplay timer started
  })();

  /* ---------- init ---------- */
  buildDots();
  setPlaying(false);   // autoplay OFF by default — presenter controls pacing
  show(0);
})();
</script>
