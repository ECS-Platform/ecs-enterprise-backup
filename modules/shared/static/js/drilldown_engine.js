/**
 * ECS Global Drilldown Engine — auto-wire metrics, charts, tables, badges to explainability modal.
 */
(function () {
  'use strict';
  if (window.__ecsDrilldownEngineInit) return;

  function esc(s) {
    return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  function parseCount(text) {
    var m = String(text || '').replace(/,/g, '').match(/(\d+(?:\.\d+)?)/);
    return m ? parseFloat(m[1]) : 0;
  }

  function slug(s) {
    return String(s || '').toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_|_$/g, '');
  }

  function pageScope() {
    var path = window.location.pathname || '';
    if (path.indexOf('/mvp/') === 0) return path.replace('/mvp/', '').split('/')[0] || 'mvp';
    if (path.indexOf('/framework/') === 0) return 'framework';
    if (path.indexOf('/dashboard') === 0) return 'dashboard';
    return path.replace(/^\//, '').split('/')[0] || 'dashboard';
  }

  function frameworkFromPage() {
    if (window.location.pathname.indexOf('/framework/') !== 0) return '';
    return decodeURIComponent(window.location.pathname.split('/framework/')[1] || '').split('?')[0];
  }

  function tableHtml(rows, cols, wrapClass) {
    if (!rows || !rows.length) return '<p class="text-muted mb-0">No supporting records.</p>';
    var h = '<div class="ecs-kpi-drill-toolbar mb-2">' +
      '<input type="search" class="form-control form-control-sm ecs-kpi-drill-search" placeholder="Search records…">' +
      '<div class="text-muted small mt-1 ecs-kpi-drill-count">' + rows.length + ' records</div></div>';
    h += '<div class="table-responsive ecs-paginated-wrap ecs-fit-view ecs-kpi-drill-table-wrap ' + (wrapClass || '') + '">' +
      '<table class="table table-sm ecs-paginated-table ecs-compact-table ecs-force-paginate mb-0"><thead><tr>';
    cols.forEach(function (c) { h += '<th>' + esc(String(c).replace(/_/g, ' ')) + '</th>'; });
    h += '</tr></thead><tbody>';
    rows.forEach(function (r) {
      h += '<tr>';
      cols.forEach(function (c) { h += '<td>' + esc(r[c]) + '</td>'; });
      h += '</tr>';
    });
    return h + '</tbody></table></div>';
  }

  function metricTraceHtml(trace) {
    if (!trace) return '';
    var h = '<div class="ecs-metric-trace mb-3">';
    h += '<h6 class="mb-2">' + esc(trace.metric_name) + '</h6>';
    if (trace.calculation_formula) {
      var f = trace.calculation_formula;
      h += '<div class="alert alert-light border py-2 px-2 mb-2 small">' +
        '<strong>Calculation Formula</strong><br>' +
        esc(f.numerator_label) + ' = ' + esc(f.implemented_controls) + '<br>' +
        esc(f.denominator_label) + ' = ' + esc(f.applicable_controls) + '<br>' +
        esc(f.formula_text) + '<br>Result = <strong>' + esc(f.result) + '</strong><br>' +
        '<span class="text-muted">' + esc(f.narrative) + '</span></div>';
    }
    if (trace.contributing_applications && trace.contributing_applications.length) {
      h += '<p class="mb-1 small"><strong>Contributing Applications:</strong> ' +
        esc(trace.contributing_applications.join(', ')) + '</p>';
    }
    if (trace.contributing_frameworks && trace.contributing_frameworks.length) {
      h += '<p class="mb-1 small"><strong>Contributing Frameworks:</strong> ' +
        esc(trace.contributing_frameworks.join(', ')) + '</p>';
    }
    if (trace.framework_contributions && trace.framework_contributions.length) {
      h += '<h6 class="text-muted small text-uppercase mt-2 mb-1">Framework Contribution</h6>';
      h += tableHtml(trace.framework_contributions,
        ['framework', 'implemented_controls', 'total_controls', 'coverage_pct']);
    }
    if (trace.justification) {
      h += '<p class="mb-2 small text-muted">' + esc(trace.justification) + '</p>';
    }
    if (trace.contributing_controls && trace.contributing_controls.length) {
      h += '<p class="mb-1 small"><strong>Contributing Controls:</strong> ' +
        esc(trace.contributing_controls.slice(0, 12).join(', ')) +
        (trace.contributing_controls.length > 12 ? '…' : '') + '</p>';
    }
    if (trace.contributing_evidence && trace.contributing_evidence.length) {
      h += '<h6 class="text-muted small text-uppercase mt-2 mb-1">Contributing Evidence</h6>';
      h += tableHtml(trace.contributing_evidence,
        ['evidence_id', 'owner', 'status', 'upload_date', 'application', 'framework']);
    }
    if (trace.related_observations && trace.related_observations.length) {
      h += '<h6 class="text-muted small text-uppercase mt-2 mb-1">Related Observations</h6>';
      h += tableHtml(trace.related_observations,
        ['observation_id', 'severity', 'application', 'framework', 'status']);
    }
    if (trace.framework_mapping) {
      var fm = trace.framework_mapping;
      h += '<p class="mb-1 small"><strong>Framework Mapping:</strong> ' +
        esc(fm.source_framework) + ' → ' + esc(fm.target_framework) +
        ' · Shared controls: ' + esc(fm.shared_controls) +
        ' · Coverage: ' + esc(fm.mapping_coverage_pct) + '%</p>';
    }
    if (trace.historical_trend && trace.historical_trend.length) {
      h += '<h6 class="text-muted small text-uppercase mt-2 mb-1">Historical Trend (6 months)</h6>';
      h += tableHtml(trace.historical_trend,
        ['month', 'value_pct', 'controls_covered', 'evidence_approved']);
    }
    if (trace.audit_trail && trace.audit_trail.length) {
      h += '<h6 class="text-muted small text-uppercase mt-2 mb-1">Audit Trail</h6>';
      h += tableHtml(trace.audit_trail,
        ['created_by', 'updated_by', 'last_reviewed', 'action', 'role']);
    }
    if (trace.gaps && trace.gaps.length) {
      h += '<h6 class="text-muted small text-uppercase mt-2 mb-1">Open Gaps</h6>';
      h += tableHtml(trace.gaps,
        ['gap_id', 'severity', 'application', 'framework', 'owner', 'description']);
    }
    h += '</div>';
    return h;
  }

  function detailHtml(detail) {
    if (!detail) return '';
    var h = '<div class="row g-2 mb-3">';
    Object.keys(detail).forEach(function (k) {
      if (typeof detail[k] === 'object') return;
      h += '<div class="col-md-3"><div class="text-muted small">' + esc(k.replace(/_/g, ' ')) +
        '</div><strong>' + esc(detail[k]) + '</strong></div>';
    });
    return h + '</div>';
  }

  function sectionsHtml(sections) {
    if (!sections) return '';
    var h = '';
    Object.keys(sections).forEach(function (name) {
      var rows = sections[name];
      if (!rows || !rows.length) return;
      var cols = Object.keys(rows[0]);
      h += '<h6 class="text-muted small text-uppercase mt-3 mb-1">' + esc(name.replace(/_/g, ' ')) + '</h6>';
      h += tableHtml(rows, cols);
    });
    return h;
  }

  function attachSearch(bodyEl) {
    var input = bodyEl.querySelector('.ecs-kpi-drill-search');
    var table = bodyEl.querySelector('.ecs-kpi-drill-table-wrap table');
    var countEl = bodyEl.querySelector('.ecs-kpi-drill-count');
    if (!input || !table || !table.tBodies.length) return;
    input.addEventListener('input', function () {
      var q = input.value.trim().toLowerCase();
      var visible = 0;
      Array.from(table.tBodies[0].rows).forEach(function (tr) {
        var match = !q || tr.textContent.toLowerCase().indexOf(q) >= 0;
        tr.style.display = match ? '' : 'none';
        if (match) visible++;
      });
      if (countEl) countEl.textContent = q ? (visible + ' matching records') : (table.tBodies[0].rows.length + ' records');
      if (window.ecsRefreshPagination) window.ecsRefreshPagination(bodyEl);
    });
  }

  function showModal(title, html) {
    var modalEl = document.getElementById('ecsUniversalDrillModal');
    var titleEl = document.getElementById('ecsUniversalDrillTitle');
    var bodyEl = document.getElementById('ecsUniversalDrillBody');
    if (!modalEl || !bodyEl || typeof bootstrap === 'undefined') return;
    titleEl.textContent = title || 'Detail';
    bodyEl.innerHTML = html;
    bodyEl.querySelectorAll('.ecs-kpi-drill-search').forEach(function (_, i, list) {
      attachSearch(bodyEl);
    });
    if (window.ecsRefreshPagination) window.ecsRefreshPagination(bodyEl);
    bootstrap.Modal.getOrCreateInstance(modalEl).show();
  }

  function renderResponse(j, title) {
    if (!j.ok) {
      showModal(title, '<p class="text-danger">' + esc(j.error || 'Failed') + '</p>');
      return;
    }
    var meta = '';
    if (j.trace_count) meta += '<span class="badge bg-info text-dark me-1">Trace: ' + j.trace_count + ' displayed</span>';
    if (j.row_count) meta += '<span class="badge bg-secondary">' + j.row_count + ' supporting records</span>';
    var html = metricTraceHtml(j.metric_trace);
    html += detailHtml(j.detail);
    if (meta) html += '<p class="mb-2">' + meta + '</p>';
    html += tableHtml(j.rows, j.columns || ['application', 'framework', 'control', 'owner', 'status', 'evidence']);
    html += sectionsHtml(j.sections);
    if (j.metric_trace && j.metric_trace.top_rejection_reasons) {
      html += '<h6 class="text-muted small text-uppercase mt-2 mb-1">Top Rejection Reasons</h6>';
      html += tableHtml(j.metric_trace.top_rejection_reasons, ['reason', 'pct', 'tooltip']);
    }
    showModal(j.title || title, html);
  }

  function fetchJson(url, title) {
    var bodyEl = document.getElementById('ecsUniversalDrillBody');
    if (bodyEl) bodyEl.innerHTML = '<div class="text-muted">Loading…</div>';
    var modalEl = document.getElementById('ecsUniversalDrillModal');
    if (modalEl && typeof bootstrap !== 'undefined') bootstrap.Modal.getOrCreateInstance(modalEl).show();
    fetch(url).then(function (r) { return r.json(); }).then(function (j) { renderResponse(j, title); })
      .catch(function () { showModal(title, '<p class="text-danger">Request failed.</p>'); });
  }

  window.ecsOpenUniversalKpiDrill = function (page, metric, label, count, framework) {
    var url = '/api/ecs/universal-drill?scope=kpi&page=' + encodeURIComponent(page || '') +
      '&metric=' + encodeURIComponent(metric || '') + '&count=' + encodeURIComponent(count || 0) +
      '&framework=' + encodeURIComponent(framework || '') + '&label=' + encodeURIComponent(label || '') +
      '&role=' + encodeURIComponent(window.__ecsRole || 'cio');
    fetchJson(url, label || metric);
  };

  window.ecsOpenUniversalRowDrill = function (page, rowType, rowId, framework) {
    fetchJson('/api/ecs/universal-drill?scope=row&page=' + encodeURIComponent(page || '') +
      '&type=' + encodeURIComponent(rowType || '') + '&id=' + encodeURIComponent(rowId || '') +
      '&framework=' + encodeURIComponent(framework || ''), rowType + ': ' + rowId);
  };

  window.ecsOpenUniversalChartDrill = function (page, chart, element, count) {
    fetchJson('/api/ecs/universal-drill?scope=chart&page=' + encodeURIComponent(page || '') +
      '&chart=' + encodeURIComponent(chart || '') + '&element=' + encodeURIComponent(element || '') +
      '&count=' + encodeURIComponent(count || 0) +
      '&role=' + encodeURIComponent(window.__ecsRole || 'cio'), chart + ' — ' + element);
  };

  window.ecsOpenHeatmapDrill = function (application, framework, readinessPct) {
    fetchJson('/api/ecs/universal-drill?scope=heatmap&application=' + encodeURIComponent(application || '') +
      '&framework=' + encodeURIComponent(framework || '') +
      '&readiness_pct=' + encodeURIComponent(readinessPct || ''), application + ' · ' + framework);
  };

  window.ecsOpenEnterpriseWorkflowDrill = function (metric, label, count) {
    fetchJson('/api/ecs/workflow-drill?metric=' + encodeURIComponent(metric || '') +
      '&count=' + encodeURIComponent(count || 0) + '&role=' + encodeURIComponent(window.__ecsRole || 'cio'),
      label || metric);
  };

  var SKIP = '[data-ecs-framework-kpi],[data-ecs-framework-wf-drill],[data-ecs-framework-row-drill],' +
    '[data-ecs-module-kpi],[data-grc-drill],[data-ecs-demo-kpi],[data-aisdlc-drill],[data-ct-drill],' +
    '[data-wf-action],[data-aisdlc-drill]';

  function bindExplicit() {
    document.addEventListener('click', function (e) {
      if (e.target.closest(SKIP)) return;
      var uk = e.target.closest('[data-ecs-universal-kpi]');
      if (uk) {
        e.preventDefault();
        ecsOpenUniversalKpiDrill(uk.getAttribute('data-ecs-universal-page'), uk.getAttribute('data-ecs-universal-metric'),
          uk.getAttribute('data-ecs-universal-label'), uk.getAttribute('data-ecs-universal-count'),
          uk.getAttribute('data-ecs-universal-framework'));
        return;
      }
      var ew = e.target.closest('[data-ecs-enterprise-wf-drill]');
      if (ew) {
        e.preventDefault();
        ecsOpenEnterpriseWorkflowDrill(ew.getAttribute('data-ecs-enterprise-wf-metric'),
          ew.getAttribute('data-ecs-enterprise-wf-label'), ew.getAttribute('data-ecs-enterprise-wf-count'));
        return;
      }
      var hm = e.target.closest('[data-ecs-heatmap-drill]');
      if (hm) {
        e.preventDefault();
        ecsOpenHeatmapDrill(hm.getAttribute('data-ecs-heatmap-app'), hm.getAttribute('data-ecs-heatmap-fw'),
          hm.getAttribute('data-ecs-heatmap-pct'));
        return;
      }
      var ur = e.target.closest('[data-ecs-universal-row]');
      if (ur) {
        if (e.target.closest('a, button, .dropdown-menu, .ecs-sticky-actions, .btn')) return;
        e.preventDefault();
        ecsOpenUniversalRowDrill(ur.getAttribute('data-ecs-universal-page'), ur.getAttribute('data-ecs-universal-type'),
          ur.getAttribute('data-ecs-universal-id'), ur.getAttribute('data-ecs-universal-framework'));
        return;
      }
      var ch = e.target.closest('[data-ecs-universal-chart]');
      if (ch) {
        e.preventDefault();
        ecsOpenUniversalChartDrill(ch.getAttribute('data-ecs-universal-page'),
          ch.getAttribute('data-ecs-universal-chart-id') || ch.getAttribute('data-ecs-universal-chart'),
          ch.getAttribute('data-ecs-universal-element'), ch.getAttribute('data-ecs-universal-count'));
      }
    });
  }

  function markDrillable(el, opts) {
    if (!el || el.hasAttribute('data-ecs-universal-kpi')) return;
    if (el.closest(SKIP)) return;
    el.classList.add('ecs-kpi-clickable');
    el.setAttribute('data-ecs-universal-kpi', '');
    el.setAttribute('data-ecs-universal-page', opts.page || pageScope());
    el.setAttribute('data-ecs-universal-metric', opts.metric || 'metric');
    el.setAttribute('data-ecs-universal-label', opts.label || 'Detail');
    el.setAttribute('data-ecs-universal-count', String(opts.count || 25));
    if (opts.framework) el.setAttribute('data-ecs-universal-framework', opts.framework);
    el.setAttribute('role', 'button');
    el.setAttribute('tabindex', '0');
    el.setAttribute('title', 'Click for supporting records');
  }

  function autoWireKpis() {
    var page = pageScope();
    var fw = frameworkFromPage();
    var selectors = [
      '.ecs-kpi-modern', '.ecs-wf-counter', '.ecs-wf-analytic-card', '.ecs-wf-queue-pill',
      '.aisdlc-kpi', '.ecs-exec-kpi', '.ecs-ob-summary-card', '.ecs-ct-summary-card',
      '.card .fs-4', '.card .fs-3', '.ecs-kpi-value', '.ecs-wf-counter-val',
      '.ecs-wf-analytic-val', '.ecs-exec-kpi-val', '.aisdlc-kpi .v', '.aisdlc-stage-card .score'
    ];
    selectors.forEach(function (sel) {
      document.querySelectorAll(sel).forEach(function (el) {
        if (el.hasAttribute('data-ecs-universal-kpi') || el.hasAttribute('data-ecs-module-kpi') ||
            el.hasAttribute('data-grc-drill') || el.hasAttribute('data-ecs-framework-kpi') ||
            el.hasAttribute('data-ecs-enterprise-wf-drill') || el.hasAttribute('data-ecs-demo-kpi') ||
            el.hasAttribute('data-aisdlc-drill')) return;
        var valEl = el.querySelector('.ecs-kpi-value, .v, .ecs-wf-counter-val, .ecs-wf-analytic-val, .ecs-exec-kpi-val, .score, .val') || el;
        var lblEl = el.querySelector('.ecs-kpi-label, .l, .ecs-wf-counter-lbl, .ecs-wf-analytic-lbl, .ecs-exec-kpi-lbl, .title, .lbl');
        var count = parseCount(valEl.textContent);
        if (!count && !lblEl) return;
        markDrillable(el, {
          page: page, framework: fw,
          metric: slug(lblEl ? lblEl.textContent : valEl.textContent),
          label: lblEl ? lblEl.textContent.trim() : 'Detail',
          count: count || 25
        });
      });
    });
  }

  function autoWireBadges() {
    var page = pageScope();
    document.querySelectorAll('.aisdlc-badge, .badge:not(.bg-secondary)').forEach(function (el) {
      if (el.closest('[data-ecs-universal-kpi]')) return;
      var t = (el.textContent || '').trim();
      if (!t || t.length > 24) return;
      if (!parseCount(t) && !/critical|high|medium|low|approved|pending|open|failed/i.test(t)) return;
      markDrillable(el, { page: page, metric: slug(t), label: t, count: parseCount(t) || 15 });
    });
  }

  function autoWireTables() {
    var page = pageScope();
    var fw = frameworkFromPage();
    document.querySelectorAll('.ecs-paginated-table tbody tr, .ecs-table-modern tbody tr, .ecs-compact-table tbody tr, .aisdlc-table tbody tr').forEach(function (tr, idx) {
      if (tr.hasAttribute('data-ecs-universal-row') || tr.hasAttribute('data-ecs-framework-row-drill') ||
          tr.hasAttribute('data-wf-id') || tr.querySelector('th')) return;
      if (tr.cells.length < 2) return;
      var rowId = (tr.cells[0].textContent || '').trim().split('\n')[0].slice(0, 80) || ('row-' + idx);
      tr.classList.add('ecs-drill-row-clickable');
      tr.setAttribute('data-ecs-universal-row', '');
      tr.setAttribute('data-ecs-universal-page', page);
      tr.setAttribute('data-ecs-universal-type', 'record');
      tr.setAttribute('data-ecs-universal-id', rowId);
      if (fw) tr.setAttribute('data-ecs-universal-framework', fw);
      tr.setAttribute('title', 'Click for full detail');
    });
  }

  function autoWireCharts() {
    var page = pageScope();
    document.querySelectorAll(
      '.ecs-trend-bar-fill, .demo-heat-cell, .ecs-insight-bar, .ecs-chart-bar, ' +
      '[data-ecs-chart-point], .aisdlc-heat-cell, .aisdlc-chart-bar .bar, .aisdlc-chart-month, ' +
      '.ecs-heat-cell, .heatmap-cell'
    ).forEach(function (el, idx) {
      if (el.hasAttribute('data-ecs-universal-chart')) return;
      var app = el.getAttribute('data-app') || el.getAttribute('data-application') || '';
      var fw = el.getAttribute('data-framework') || el.getAttribute('data-fw') || frameworkFromPage();
      var pct = el.getAttribute('data-pct') || el.getAttribute('data-readiness') || el.textContent.trim();
      if (app && fw && parseCount(pct)) {
        el.setAttribute('data-ecs-heatmap-drill', '');
        el.setAttribute('data-ecs-heatmap-app', app);
        el.setAttribute('data-ecs-heatmap-fw', fw);
        el.setAttribute('data-ecs-heatmap-pct', pct);
      } else {
        el.setAttribute('data-ecs-universal-chart', '');
        el.setAttribute('data-ecs-universal-page', page);
        el.setAttribute('data-ecs-universal-chart-id', (el.closest('[data-chart-id]') || {}).getAttribute ?
          el.closest('[data-chart-id]').getAttribute('data-chart-id') : 'chart');
        el.setAttribute('data-ecs-universal-element', el.getAttribute('title') || el.textContent.trim() || ('point-' + idx));
        el.setAttribute('data-ecs-universal-count', String(parseCount(el.textContent) || 25));
      }
      el.style.cursor = 'pointer';
      el.setAttribute('title', (el.getAttribute('title') || 'Metric') + ' — click for records');
    });
  }

  function init() {
    if (typeof bootstrap === 'undefined') { setTimeout(init, 40); return; }
    window.__ecsDrilldownEngineInit = true;
    window.__ecsUniversalDrillInit = true;
    bindExplicit();
    autoWireKpis();
    autoWireBadges();
    autoWireTables();
    autoWireCharts();
    document.addEventListener('ecsDrillTabSwitch', function () {
      setTimeout(function () { autoWireKpis(); autoWireBadges(); autoWireTables(); autoWireCharts(); }, 60);
    });
    if (typeof MutationObserver !== 'undefined') {
      var timer;
      var obs = new MutationObserver(function () {
        clearTimeout(timer);
        timer = setTimeout(function () { autoWireKpis(); autoWireBadges(); autoWireTables(); autoWireCharts(); }, 150);
      });
      obs.observe(document.body, { childList: true, subtree: true });
    }
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
