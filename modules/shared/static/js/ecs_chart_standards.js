/*
 * ECS Chart Accessibility & Configuration Validation Utilities
 * Release: ecs-chart-accessibility-remediation-v1
 *
 * Vendored, dependency-free utilities that enforce the ECS chart standard:
 *   - validateContrast(fg, bg)            -> WCAG contrast ratio + pass flags
 *   - validateChartAccessibility(el)      -> per-chart accessibility audit
 *   - validateChartConfiguration(cfg)     -> chart config (title/axes/legend/...) audit
 *
 * All functions are pure and fail-safe. In the browser they attach to
 * window.ECSChartStandards and can audit live DOM. In a headless/test context
 * they accept plain objects so they can run without a DOM.
 */
(function (root, factory) {
  var api = factory();
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  if (root) root.ECSChartStandards = api;
})(typeof window !== 'undefined' ? window : this, function () {
  'use strict';

  var WCAG_AA = 4.5;
  var WCAG_AA_LARGE = 3.0;
  var WCAG_AAA = 7.0;

  // ── Color parsing & relative luminance (WCAG 2.x) ──────────────────────────
  function _hexToRgb(hex) {
    if (typeof hex !== 'string') return null;
    var h = hex.trim().replace(/^#/, '');
    if (h.length === 3) h = h.split('').map(function (c) { return c + c; }).join('');
    if (!/^[0-9a-fA-F]{6}$/.test(h)) return null;
    return { r: parseInt(h.slice(0, 2), 16), g: parseInt(h.slice(2, 4), 16), b: parseInt(h.slice(4, 6), 16) };
  }

  function _parseColor(color) {
    if (!color) return null;
    if (color.charAt && color.charAt(0) === '#') return _hexToRgb(color);
    var m = String(color).match(/rgba?\(\s*(\d+)[,\s]+(\d+)[,\s]+(\d+)/i);
    if (m) return { r: +m[1], g: +m[2], b: +m[3] };
    return _hexToRgb(color);
  }

  function _channel(c) {
    var s = c / 255;
    return s <= 0.03928 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4);
  }

  function _luminance(rgb) {
    return 0.2126 * _channel(rgb.r) + 0.7152 * _channel(rgb.g) + 0.0722 * _channel(rgb.b);
  }

  /**
   * Contrast ratio between a foreground and background color.
   * @returns {{ratio:number, AA:boolean, AAA:boolean, AA_large:boolean, fg, bg, valid:boolean}}
   */
  function validateContrast(fg, bg, opts) {
    opts = opts || {};
    var f = _parseColor(fg), b = _parseColor(bg);
    if (!f || !b) {
      return { ratio: 0, AA: false, AAA: false, AA_large: false, fg: fg, bg: bg, valid: false, reason: 'unparseable color' };
    }
    var lf = _luminance(f), lb = _luminance(b);
    var ratio = (Math.max(lf, lb) + 0.05) / (Math.min(lf, lb) + 0.05);
    ratio = Math.round(ratio * 100) / 100;
    var minRequired = opts.large ? WCAG_AA_LARGE : WCAG_AA;
    return {
      ratio: ratio,
      AA: ratio >= (opts.large ? WCAG_AA_LARGE : WCAG_AA),
      AAA: ratio >= WCAG_AAA,
      AA_large: ratio >= WCAG_AA_LARGE,
      fg: fg, bg: bg, valid: true,
      passes: ratio >= minRequired
    };
  }

  // ── DOM helpers (no-op safe when no DOM) ───────────────────────────────────
  function _hasDom() { return typeof document !== 'undefined' && !!document; }
  function _computed(el, prop) {
    if (!_hasDom() || !el || !window.getComputedStyle) return '';
    try { return window.getComputedStyle(el).getPropertyValue(prop); } catch (e) { return ''; }
  }
  function _effectiveBg(el) {
    var node = el;
    while (node && node.nodeType === 1) {
      var bg = _computed(node, 'background-color');
      var rgb = _parseColor(bg);
      if (rgb && !/rgba\([^)]*,\s*0\s*\)/i.test(bg)) return bg;
      node = node.parentElement;
    }
    return '#ffffff';
  }

  /**
   * Audit a chart element (or descriptor) for accessibility requirements.
   * Accepts a DOM element OR a plain descriptor:
   *   { title, subtitle, xLabel, yLabel, yScale, legend, tooltip,
   *     labelsVisible, labelsOverlap }
   * @returns {{passed:boolean, errors:string[], warnings:string[], checks:object}}
   */
  function validateChartAccessibility(input) {
    var errors = [], warnings = [], checks = {};

    if (input && input.nodeType === 1) {
      // Live DOM audit.
      var card = input.closest ? (input.closest('.chart-card, .executive-analytics-card, .ecs-analytics-chart-card') || input.parentElement) : input.parentElement;
      var titleEl = card && card.querySelector ? card.querySelector('.chart-card-title, .ecs-hub-chart-title, .ecs-chart-title') : null;
      var subEl = card && card.querySelector ? card.querySelector('.chart-card-subtitle, .chart-def, .ecs-chart-subtitle') : null;
      var legendEl = card && card.querySelector ? card.querySelector('.ecs-chart-legend, .ecs-obs-legend, .ecs-legend') : null;
      var frame = document.getElementById(input.id + '__frame');
      var yLabelEl = frame ? frame.querySelector('.ecs-chart-yaxis-label') : null;
      var xLabelEl = frame ? frame.querySelector('.ecs-chart-xaxis-label') : null;
      var yScaleEl = input.querySelector ? input.querySelector('.ecs-chart-yscale') : null;
      var bars = input.querySelectorAll ? input.querySelectorAll('.ecs-bar-col, .trend-bar, .ecs-insight-bar') : [];
      var withTip = 0;
      Array.prototype.forEach.call(bars, function (b) { if (b.getAttribute && b.getAttribute('title')) withTip++; });

      checks = {
        title: !!(titleEl && titleEl.textContent.trim()),
        subtitle: !!(subEl && subEl.textContent.trim()),
        yLabel: !!(yLabelEl && yLabelEl.textContent.trim()),
        xLabel: !!(xLabelEl && xLabelEl.textContent.trim()),
        yScale: !!(yScaleEl && yScaleEl.children.length),
        legend: !!(legendEl && legendEl.textContent.trim()),
        tooltip: bars.length > 0 && withTip === bars.length,
        labelsVisible: bars.length > 0
      };
    } else {
      var d = input || {};
      checks = {
        title: !!d.title, subtitle: !!d.subtitle, yLabel: !!d.yLabel, xLabel: !!d.xLabel,
        yScale: !!d.yScale, legend: !!d.legend, tooltip: !!d.tooltip,
        labelsVisible: d.labelsVisible !== false, labelsOverlap: !!d.labelsOverlap
      };
    }

    if (!checks.title) errors.push('Missing chart title');
    if (!checks.subtitle) errors.push('Missing chart subtitle');
    if (!checks.xLabel) errors.push('Missing X-axis label');
    if (!checks.yLabel) errors.push('Missing Y-axis label');
    if (!checks.yScale) errors.push('Missing Y-axis scale');
    if (!checks.legend) errors.push('Missing legend');
    if (!checks.tooltip) errors.push('Missing tooltip support');
    if (checks.labelsVisible === false) errors.push('Hidden labels');
    if (checks.labelsOverlap) errors.push('Overlapping labels');

    return { passed: errors.length === 0, errors: errors, warnings: warnings, checks: checks };
  }

  /**
   * Validate a chart configuration object BEFORE render.
   * Required: title, subtitle, xLabel, yLabel, yScale (or autoScale), legend, tooltip.
   * @returns {{passed:boolean, errors:string[]}}
   */
  function validateChartConfiguration(cfg) {
    cfg = cfg || {};
    var errors = [];
    var title = cfg.title || cfg.chartTitle;
    var subtitle = cfg.subtitle || cfg.chartSubtitle;
    var xLabel = cfg.xLabel || cfg.xAxisLabel;
    var yLabel = cfg.yLabel || cfg.yAxisLabel;
    var yScale = cfg.yScale || cfg.autoScale || cfg.yTicks;
    var legend = cfg.legend !== false && (cfg.legend || cfg.seriesLabel || cfg.series);
    var tooltip = cfg.tooltip !== false;

    if (!title) errors.push('Missing chart title');
    if (!subtitle) errors.push('Missing chart subtitle');
    if (!xLabel) errors.push('Missing X-axis label');
    if (!yLabel) errors.push('Missing Y-axis label');
    if (!yScale) errors.push('Missing Y-axis scale');
    if (!legend) errors.push('Missing legend');
    if (!tooltip) errors.push('Missing tooltip support');

    return { passed: errors.length === 0, errors: errors };
  }

  /**
   * Validate a navigation tab (or descriptor) for accessibility.
   * Accepts a DOM element OR a descriptor:
   *   { inactiveFg, inactiveBg, activeFg, activeBg, hoverFg, hoverBg,
   *     disabledFg, disabledBg }
   * Rules (P1 sub-nav contrast fix):
   *   - text color must NOT equal background color
   *   - inactive/active/hover contrast >= 4.5:1
   *   - active state must be distinguishable from inactive (different bg)
   * @returns {{passed:boolean, errors:string[], ratios:object}}
   */
  function validateTabAccessibility(input) {
    var errors = [], ratios = {};
    var states;

    if (input && input.nodeType === 1 && _hasDom()) {
      // Live DOM: read inactive + active (toggle a temporary class is unsafe, so
      // read the element as-is plus its .is-active/.active sibling if present).
      var fg = (_computed(input, 'color') || '').trim();
      var bg = _effectiveBg(input);
      var isActive = input.classList.contains('is-active') || input.classList.contains('active') ||
                     input.getAttribute('aria-selected') === 'true';
      states = {};
      states[isActive ? 'active' : 'inactive'] = { fg: fg, bg: bg };
      // Try to find a sibling in the opposite state for comparison.
      var sibs = input.parentElement ? input.parentElement.querySelectorAll('.ecs-workspace-tab, .ecs-tab, .nav-link') : [];
      Array.prototype.forEach.call(sibs, function (s) {
        if (s === input) return;
        var sActive = s.classList.contains('is-active') || s.classList.contains('active') ||
                      s.getAttribute('aria-selected') === 'true';
        var key = sActive ? 'active' : 'inactive';
        if (!states[key]) states[key] = { fg: (_computed(s, 'color') || '').trim(), bg: _effectiveBg(s) };
      });
    } else {
      var d = input || {};
      states = {
        inactive: (d.inactiveFg && d.inactiveBg) ? { fg: d.inactiveFg, bg: d.inactiveBg } : null,
        active: (d.activeFg && d.activeBg) ? { fg: d.activeFg, bg: d.activeBg } : null,
        hover: (d.hoverFg && d.hoverBg) ? { fg: d.hoverFg, bg: d.hoverBg } : null,
        disabled: (d.disabledFg && d.disabledBg) ? { fg: d.disabledFg, bg: d.disabledBg } : null
      };
    }

    ['inactive', 'active', 'hover', 'disabled'].forEach(function (state) {
      var s = states[state];
      if (!s) return;
      var c = validateContrast(s.fg, s.bg);
      ratios[state] = c.ratio;
      var fgRgb = _parseColor(s.fg), bgRgb = _parseColor(s.bg);
      if (fgRgb && bgRgb && fgRgb.r === bgRgb.r && fgRgb.g === bgRgb.g && fgRgb.b === bgRgb.b) {
        errors.push(state + ': text color equals background color');
      } else if (c.valid && c.ratio < WCAG_AA && state !== 'disabled') {
        errors.push(state + ': contrast ' + c.ratio + ' < 4.5:1');
      } else if (state === 'disabled' && c.valid && c.ratio < WCAG_AA_LARGE) {
        errors.push('disabled: contrast ' + c.ratio + ' below 3:1');
      }
    });

    // Active must be distinguishable from inactive.
    if (states.active && states.inactive) {
      var a = _parseColor(states.active.bg), i = _parseColor(states.inactive.bg);
      if (a && i && a.r === i.r && a.g === i.g && a.b === i.b) {
        errors.push('active state not distinguishable from inactive (same background)');
      }
    }

    return { passed: errors.length === 0, errors: errors, ratios: ratios };
  }

  /**
   * Audit every chart on the current page (browser only). Returns a report array.
   * Useful from the console: ECSChartStandards.auditPage().
   */
  function auditPage() {
    if (!_hasDom()) return [];
    var nodes = document.querySelectorAll('.ecs-bar-chart, .mini-bar-chart, .trend-chart, [data-ecs-chart]');
    return Array.prototype.map.call(nodes, function (el) {
      return { id: el.id || '(anonymous)', result: validateChartAccessibility(el) };
    });
  }

  return {
    version: 'ecs-chart-accessibility-remediation-v1',
    WCAG_AA: WCAG_AA, WCAG_AAA: WCAG_AAA, WCAG_AA_LARGE: WCAG_AA_LARGE,
    validateContrast: validateContrast,
    validateChartAccessibility: validateChartAccessibility,
    validateChartConfiguration: validateChartConfiguration,
    validateTabAccessibility: validateTabAccessibility,
    auditPage: auditPage,
    // exposed for testing
    _parseColor: _parseColor
  };
});
