<script setup>
// The offline map: the scroll walks the real way up Big Chimgan — the fastest path over the trail
// graph of the app's region pack — while the camera follows, springs and camps come up along it and
// the profile below keeps pace. A finger on the profile moves a point on the map, as in the app.
import { computed, inject, onBeforeUnmount, reactive, ref } from 'vue';

import { gsap, reduced, ScrollTrigger, useMotion } from '../composables/motion.js';
import { SUMMIT } from '../config.js';
import poisData from '../data/pois.json';
import route from '../data/route.json';
import { lang, t } from '../i18n/index.js';
import { clamp, dec, deg, lerp, num } from '../lib/format.js';
import { TopoMap } from '../lib/topo.js';
import MarkLabel from './MarkLabel.vue';
import RollingNumber from './RollingNumber.vue';

const terrain = inject('terrain');

// ── the route ──────────────────────────────────────────────────────────────────
const total = route.lengthM;
const rawTop = route.points[route.points.length - 1][2];
// [x, y, ele, dist, hours] in map space; the DEM rounds the summit off, the catalog says 3 309 m
const pts = route.points.map(([gx, gy, ele, dist]) => [gx + 0.5, gy + 0.5, ele + (SUMMIT - rawTop) * (dist / total) ** 3, dist, 0]);
for (let i = 1; i < pts.length; i++) {
  const d = pts[i][3] - pts[i - 1][3];
  const slope = d ? (pts[i][2] - pts[i - 1][2]) / d : 0;
  pts[i][4] = pts[i - 1][4] + d / 1000 / (6 * Math.exp(-3.5 * Math.abs(slope + 0.05))); // Tobler's hiking function
}
const hours = pts[pts.length - 1][4];
const startEle = pts[0][2];

function at(fraction) {
  const f = clamp(fraction) * (pts.length - 1);
  const i = Math.min(pts.length - 2, Math.floor(f));
  const k = f - i;
  return pts[i].map((v, n) => lerp(v, pts[i + 1][n], k));
}

// Springs, camps and passes within ~450 m of the way, each tied to the point where the route reaches it
const pois = poisData
  .filter((p) => ['spring', 'camp', 'pass', 'hut', 'shelter', 'waterfall'].includes(p.k))
  .map((p) => {
    let best = Infinity;
    let index = 0;
    pts.forEach((q, i) => {
      const d = Math.hypot(q[0] - p.x - 0.5, q[1] - p.y - 0.5);
      if (d < best) [best, index] = [d, i];
    });
    return { kind: p.k, x: p.x + 0.5, y: p.y + 0.5, d: best, at: index / (pts.length - 1) };
  })
  .filter((p) => p.d < 22);

// ── state ──────────────────────────────────────────────────────────────────────
const progress = ref(0);
const peek = ref(null); // a fraction of the route under the finger on the profile
const here = computed(() => at(progress.value));
const stats = computed(() => {
  const [, , ele, dist, time] = here.value;
  const left = hours - time;
  const h = Math.floor(left);
  const m = Math.round(((left - h) * 60) / 5) * 5;
  return {
    km: dec(dist / 1000, lang),
    gain: num(Math.max(0, ele - startEle)),
    alt: num(ele),
    left: left < 0.04 ? t('rt.top') : `${h + (m === 60 ? 1 : 0)} ${t('unit.h')} ${two(m === 60 ? 0 : m)} ${t('unit.min')}`,
  };
});
const two = (n) => String(n).padStart(2, '0');
const steps = t('rt.steps');
const step = computed(() => Math.min(steps.length - 1, Math.floor(progress.value * steps.length)));

// ── the profile ────────────────────────────────────────────────────────────────
const PW = 1000;
const PH = 120;
const px = (dist) => (dist / total) * PW;
const py = (ele) => PH - 8 - ((ele - 1650) / (SUMMIT - 1650)) * (PH - 16);
const profileLine = pts.filter((_, i) => i % 2 === 0 || i === pts.length - 1).map((p, i) => `${i ? 'L' : 'M'}${px(p[3]).toFixed(1)} ${py(p[2]).toFixed(1)}`).join(' ');
const profileArea = `${profileLine} L${PW} ${PH} L0 ${PH} Z`;
const tip = computed(() => {
  if (peek.value == null) return null;
  const [, , ele, dist, time] = at(peek.value);
  const clock = 6.5 + time; // out at 06:30
  const temp = 5.2 - 0.0065 * (ele - 1600) + Math.min(4, time * 1.1); // the example day warms towards noon
  return {
    left: `${peek.value * 100}%`,
    text: `${num(ele)} ${t('unit.m')} · ${dec(dist / 1000, lang)} ${t('unit.km')} · ${deg(temp)} ${t('tip.at')} ${two(Math.floor(clock))}:${two(Math.floor((clock % 1) * 60))}`,
  };
});
function onProfile(event) {
  const rect = event.currentTarget.getBoundingClientRect();
  peek.value = clamp((event.clientX - rect.left) / rect.width);
  draw();
}
function offProfile() {
  peek.value = null;
  draw();
}

// ── the map ────────────────────────────────────────────────────────────────────
const pin = ref(null);
const canvas = ref(null);
const labels = reactive({ a: [0, 0], peak: [0, 0], on: false });
let map = null;
let observer = null;

const INK = { glacier: '#1FBFB8', night: '#020A2E', frost: '#E6F2F2', frost2: '#A9BCD6', water: '#5FB7E0' };

function layer(ctx, m, f) {
  const sx = (x) => x * f.scale + f.tx;
  const sy = (y) => y * f.scale + f.ty;
  const r = progress.value;
  const head = here.value;
  const reached = Math.floor(clamp(r) * (pts.length - 1));
  ctx.save();
  ctx.setTransform(m.dpr, 0, 0, m.dpr, 0, 0);
  ctx.lineJoin = 'round';
  ctx.lineCap = 'round';

  // the way still ahead
  ctx.beginPath();
  pts.forEach((p, i) => (i ? ctx.lineTo(sx(p[0]), sy(p[1])) : ctx.moveTo(sx(p[0]), sy(p[1]))));
  ctx.setLineDash([2, 6]);
  ctx.lineWidth = 1.5;
  ctx.strokeStyle = 'rgba(169, 188, 214, 0.55)';
  ctx.stroke();
  ctx.setLineDash([]);

  // points of interest come up as the route gets near
  for (const p of pois) {
    const a = clamp((r - p.at) * 26 + 1);
    if (a <= 0) continue;
    const x = sx(p.x);
    const y = sy(p.y);
    const s = 0.6 + 0.4 * a;
    ctx.globalAlpha = a;
    ctx.lineWidth = 1.5;
    if (p.kind === 'spring' || p.kind === 'waterfall') {
      ctx.beginPath();
      ctx.arc(x, y, 3.6 * s, 0, Math.PI * 2);
      ctx.fillStyle = INK.water;
      ctx.strokeStyle = INK.night;
      ctx.fill();
      ctx.stroke();
    } else if (p.kind === 'pass') {
      ctx.beginPath();
      ctx.moveTo(x - 4 * s, y - 4 * s);
      ctx.lineTo(x + 4 * s, y + 4 * s);
      ctx.moveTo(x + 4 * s, y - 4 * s);
      ctx.lineTo(x - 4 * s, y + 4 * s);
      ctx.strokeStyle = INK.frost2;
      ctx.stroke();
    } else {
      ctx.beginPath();
      ctx.moveTo(x - 5.5 * s, y + 4.5 * s);
      ctx.lineTo(x, y - 5 * s);
      ctx.lineTo(x + 5.5 * s, y + 4.5 * s);
      ctx.closePath();
      ctx.fillStyle = INK.night;
      ctx.strokeStyle = INK.frost;
      ctx.fill();
      ctx.stroke();
    }
  }
  ctx.globalAlpha = 1;

  // the way walked
  if (r > 0) {
    ctx.beginPath();
    for (let i = 0; i <= reached; i++) (i ? ctx.lineTo(sx(pts[i][0]), sy(pts[i][1])) : ctx.moveTo(sx(pts[i][0]), sy(pts[i][1])));
    ctx.lineTo(sx(head[0]), sy(head[1]));
    ctx.lineWidth = 7;
    ctx.strokeStyle = INK.night;
    ctx.stroke();
    ctx.lineWidth = 3;
    ctx.strokeStyle = INK.glacier;
    ctx.stroke();
  }

  const mark = (p, radius, fill) => {
    ctx.beginPath();
    ctx.arc(sx(p[0]), sy(p[1]), radius, 0, Math.PI * 2);
    ctx.fillStyle = fill;
    ctx.fill();
  };
  if (peek.value != null) {
    const ghost = at(peek.value);
    mark(ghost, 8, INK.night);
    mark(ghost, 5, INK.frost);
  }
  mark(head, 15, 'rgba(31, 191, 184, 0.22)');
  mark(head, 8.5, INK.night);
  mark(head, 6, INK.glacier);
  ctx.restore();
}

function camera() {
  if (!map) return;
  const wide = innerWidth > 900;
  const k = gsap.parseEase('power2.inOut')(clamp(progress.value * 2.4));
  const head = here.value;
  map.setView({
    x: lerp(terrain.value.w / 2, head[0], k),
    y: lerp(terrain.value.h / 2, head[1], k),
    zoom: 1 + (wide ? 0.8 : 1.5) * k,
    ax: wide ? 0.44 : 0.5,
    ay: wide ? 0.5 : 0.4,
  });
}

function draw() {
  if (!map) return;
  camera();
  map.draw(true);
}

useMotion(() => {
  if (terrain.value) {
    map = new TopoMap(canvas.value, terrain.value, 'dark');
    map.layers.push(layer);
    map.onDraw = (m) => {
      const a = m.project(pts[0][0], pts[0][1]);
      const top = m.project(pts[pts.length - 1][0], pts[pts.length - 1][1]);
      labels.a = [a[0] - 11, a[1] - 11];
      labels.peak = [top[0] - 8, top[1] - 30];
      labels.on = true;
    };
    draw();
    let timer;
    observer = new ResizeObserver(() => {
      clearTimeout(timer);
      timer = setTimeout(() => {
        map.resize();
        draw();
      }, 80);
    });
    observer.observe(canvas.value);
  }

  ScrollTrigger.create({
    trigger: pin.value, start: 'top top', end: reduced ? '+=120%' : '+=320%', pin: true, scrub: true,
    onUpdate: (self) => {
      progress.value = clamp((self.progress - 0.05) / 0.87);
      draw();
    },
  });
});

onBeforeUnmount(() => observer?.disconnect());
</script>

<template>
  <section id="map" class="route" data-theme="dark">
    <div ref="pin" class="route__pin">
      <canvas ref="canvas" class="route__canvas"></canvas>
      <span class="map-label map-label--dark map-label--a" :style="{ transform: `translate(${labels.a[0]}px, ${labels.a[1]}px)`, opacity: labels.on ? 1 : 0 }">
        <b>A</b><i class="mono">{{ num(startEle) }}</i>
      </span>
      <span class="map-label map-label--dark" :style="{ transform: `translate(${labels.peak[0]}px, ${labels.peak[1]}px)`, opacity: labels.on ? 1 : 0 }">
        <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true"><path d="M2 20 9 7l4 7 3-4.500L22 20Z" /></svg>
        <b>{{ t('hero.peak') }}</b><i class="mono">{{ num(SUMMIT) }}</i>
      </span>

      <div class="route__head">
        <MarkLabel :name="t('rt.label')" />
        <h2 v-split class="title">{{ t('rt.title') }}</h2>
        <span class="chip chip--air mono">
          <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true"><path d="M3 13.500 21 4l-5 17-4-7-9-.500Z" /></svg>
          {{ t('rt.offline') }}
        </span>
      </div>

      <ol class="steps">
        <li v-for="(item, i) in steps" :key="i" :class="{ 'is-on': i === step }">
          <i class="mono">{{ i + 1 }}</i><b>{{ item[0] }}</b><span><em>{{ item[1] }}</em></span>
        </li>
      </ol>

      <div class="sheet">
        <dl class="sheet__stats">
          <div><dt class="mono">{{ t('rt.done') }}</dt><dd class="mono"><RollingNumber :value="stats.km" /> <small>{{ t('unit.km') }}</small></dd></div>
          <div><dt class="mono">{{ t('rt.gain') }}</dt><dd class="mono"><RollingNumber :value="stats.gain" /> <small>{{ t('unit.m') }}</small></dd></div>
          <div><dt class="mono">{{ t('rt.alt') }}</dt><dd class="mono"><RollingNumber :value="stats.alt" /> <small>{{ t('unit.m') }}</small></dd></div>
          <div><dt class="mono">{{ t('rt.left') }}</dt><dd class="mono"><RollingNumber :value="stats.left" /></dd></div>
        </dl>
        <div class="profile" @pointermove="onProfile" @pointerleave="offProfile">
          <svg class="profile__svg" :viewBox="`0 0 ${PW} ${PH}`" preserveAspectRatio="none" aria-hidden="true">
            <defs>
              <clipPath id="profile-done"><rect x="0" y="0" :width="px(here[3])" :height="PH" /></clipPath>
            </defs>
            <path :d="profileArea" fill="#102358" />
            <path :d="profileArea" fill="rgba(31,191,184,.3)" clip-path="url(#profile-done)" />
            <path :d="profileLine" fill="none" stroke="#1C2C63" stroke-width="1.5" vector-effect="non-scaling-stroke" />
            <path :d="profileLine" fill="none" stroke="#1FBFB8" stroke-width="2" vector-effect="non-scaling-stroke" clip-path="url(#profile-done)" />
            <line :x1="px(here[3])" :x2="px(here[3])" y1="0" :y2="PH" stroke="#1FBFB8" stroke-width="1" vector-effect="non-scaling-stroke" />
            <line v-if="peek != null" :x1="peek * PW" :x2="peek * PW" y1="0" :y2="PH" stroke="#E6F2F2" stroke-width="1" vector-effect="non-scaling-stroke" />
          </svg>
          <span class="profile__tip mono" :style="{ left: tip?.left, opacity: tip ? 1 : 0 }">{{ tip?.text }}</span>
        </div>
      </div>
    </div>
  </section>
</template>
