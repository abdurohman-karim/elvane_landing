<script setup>
// The hero is a live map sheet: the real relief of Big Chimgan fills with contours from the valley up,
// and the contour under the cursor lights up with its height and coordinates.
import { inject, onBeforeUnmount, onMounted, reactive, ref } from 'vue';

import { gsap, reduced, ScrollTrigger } from '../composables/motion.js';
import { STORE_URL } from '../config.js';
import route from '../data/route.json';
import { t } from '../i18n/index.js';
import { num } from '../lib/format.js';
import { TopoMap } from '../lib/topo.js';

const terrain = inject('terrain');

const section = ref(null);
const mapEl = ref(null);
const baseCanvas = ref(null);
const overCanvas = ref(null);
const title = ref(null);
const body = ref(null);
const foot = ref(null);

const readout = reactive({ on: false, x: 0, y: 0, ele: '', pos: '' });
const peak = reactive({ x: 0, y: 0, on: false });
const scale = reactive({ width: 80, label: '' });

const last = route.points[route.points.length - 1];
const summit = [last[0] + 0.5, last[1] + 0.5];

let map = null;
let context = null;
let observer = null;
let tick = null;
const pointer = { x: 0, y: 0, hover: false, level: null, visible: true, t: 0 };

function place() {
  const wide = innerWidth > 900;
  // The summit sits to the right of the headline, the valley runs off to the left
  map.setView({ x: summit[0], y: summit[1], ax: wide ? 0.7 : 0.55, ay: wide ? 0.44 : 0.3, zoom: wide ? 1.08 : 1.6 });
}

function drawOver() {
  const canvas = overCanvas.value;
  const ctx = canvas.getContext('2d');
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  if (map.reveal < 1 || pointer.level == null) return;
  const f = map.frame();
  ctx.setTransform(map.dpr * f.scale, 0, 0, map.dpr * f.scale, map.dpr * f.tx, map.dpr * f.ty);
  ctx.lineJoin = 'round';
  ctx.lineWidth = (pointer.hover ? 2 : 1.5) / f.scale;
  ctx.strokeStyle = pointer.level >= 3000 ? '#1978A5' : '#05716C';
  ctx.stroke(terrain.value.iso(pointer.level));
  if (!pointer.hover) return;
  ctx.setTransform(map.dpr, 0, 0, map.dpr, 0, 0);
  ctx.strokeStyle = '#031163';
  ctx.lineWidth = 1;
  ctx.beginPath();
  for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
    ctx.moveTo(pointer.x + dx * 5, pointer.y + dy * 5);
    ctx.lineTo(pointer.x + dx * 14, pointer.y + dy * 14);
  }
  ctx.stroke();
}

function onMove(event) {
  if (!map || event.pointerType === 'touch') return;
  const rect = mapEl.value.getBoundingClientRect();
  const zoom = rect.width / map.W; // the map scales a little while the page scrolls
  pointer.x = (event.clientX - rect.left) / zoom;
  pointer.y = (event.clientY - rect.top) / zoom;
  pointer.hover = true;
  const [mx, my] = map.unproject(pointer.x, pointer.y);
  pointer.level = terrain.value.eleAt(mx, my);
  const [lon, lat] = terrain.value.lonLat(mx, my);
  const box = section.value.getBoundingClientRect();
  readout.ele = `${num(pointer.level)} ${t('unit.m')}`;
  readout.pos = `${lat.toFixed(5)}° N · ${lon.toFixed(5)}° E`;
  readout.x = event.clientX - box.left + (event.clientX > innerWidth - 230 ? -196 : 18);
  readout.y = event.clientY - box.top + (event.clientY - box.top > box.height - 90 ? -64 : 18);
  readout.on = true;
  drawOver();
}

function onLeave() {
  pointer.hover = false;
  readout.on = false;
}

onMounted(() => {
  context = gsap.context(() => {
    if (!reduced) {
      gsap.set(title.value.querySelectorAll('.line'), { yPercent: 110 });
      gsap.set(body.value.querySelectorAll('[data-in]'), { y: 24, opacity: 0 });
      gsap.set(foot.value, { opacity: 0 });
    }

    if (!terrain.value) return;
    map = new TopoMap(baseCanvas.value, terrain.value, 'light');
    map.reveal = reduced ? 1 : 0;
    map.onDraw = (m, f) => {
      const [px, py] = m.project(summit[0], summit[1]);
      peak.x = px - 8;
      peak.y = py - 10;
      const metres = (80 / f.scale) * terrain.value.metresPerCell;
      const nice = [100, 200, 250, 500, 1000, 2000].reduce((a, b) => (Math.abs(b - metres) < Math.abs(a - metres) ? b : a));
      scale.width = (nice / terrain.value.metresPerCell) * f.scale;
      scale.label = nice >= 1000 ? `${nice / 1000} ${t('unit.km')}` : `${nice} ${t('unit.m')}`;
    };
    const fit = () => {
      map.resize();
      place();
      overCanvas.value.width = map.canvas.width;
      overCanvas.value.height = map.canvas.height;
      map.draw(true);
      drawOver();
    };
    fit();

    let timer;
    observer = new ResizeObserver(() => {
      clearTimeout(timer);
      timer = setTimeout(fit, 80);
    });
    observer.observe(mapEl.value);

    ScrollTrigger.create({
      trigger: section.value, start: 'top bottom', end: 'bottom top',
      onToggle: (self) => (pointer.visible = self.isActive),
    });

    if (reduced) return;
    // With no cursor on the map a contour climbs the mountain and comes back down on its own
    tick = (time) => {
      if (pointer.hover || !pointer.visible || map.reveal < 1 || time - pointer.t < 1 / 30) return;
      pointer.t = time;
      const span = terrain.value.max - terrain.value.min - 60;
      const phase = (time * 0.035) % 1;
      pointer.level = terrain.value.min + 40 + span * (phase < 0.5 ? phase * 2 : 2 - phase * 2);
      drawOver();
    };
    gsap.ticker.add(tick);

    const scrub = { trigger: section.value, start: 'top top', end: 'bottom top', scrub: true };
    gsap.to(mapEl.value, { yPercent: 14, scale: 1.1, ease: 'none', scrollTrigger: scrub });
    gsap.to(body.value, { yPercent: -12, ease: 'none', scrollTrigger: { ...scrub } });
  }, section.value);
});

onBeforeUnmount(() => {
  if (tick) gsap.ticker.remove(tick);
  observer?.disconnect();
  context?.revert();
});

/** The entrance, played by App under the intro as it lifts. */
function enter() {
  const timeline = gsap.timeline();
  if (map) timeline.to(map, { reveal: 1, duration: 2, ease: 'power2.inOut', onUpdate: () => map.draw(true) }, 0);
  timeline
    .to(title.value.querySelectorAll('.line'), { yPercent: 0, duration: 1.15, stagger: 0.1, ease: 'power4.out' }, 0.55)
    .to(body.value.querySelectorAll('[data-in]'), { y: 0, opacity: 1, duration: 0.9, stagger: 0.08 }, 0.85)
    .to(foot.value, { opacity: 1, duration: 0.6 }, 1.3)
    .add(() => (peak.on = true), 1.5);
  return timeline;
}

function show() {
  peak.on = true;
}

defineExpose({ enter, show });
</script>

<template>
  <section id="top" ref="section" class="hero" data-theme="light">
    <div ref="mapEl" class="hero__map" @pointermove="onMove" @pointerleave="onLeave">
      <canvas ref="baseCanvas" class="hero__canvas"></canvas>
      <canvas ref="overCanvas" class="hero__canvas hero__canvas--over"></canvas>
      <span class="map-label map-label--peak" :style="{ transform: `translate(${peak.x}px, ${peak.y}px)`, opacity: peak.on ? 1 : 0 }">
        <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true"><path d="M2 20 9 7l4 7 3-4.500L22 20Z" /></svg>
        <b>{{ t('hero.peak') }}</b><i class="mono">3 309</i>
      </span>
    </div>

    <div ref="body" class="hero__body">
      <p class="eyebrow mono" data-in>{{ t('hero.eyebrow') }}</p>
      <h1 ref="title" class="display">
        <span v-for="line in t('hero.title')" :key="line" class="line-mask"><span class="line">{{ line }}</span>{{ ' ' }}</span>
      </h1>
      <p class="hero__lede" data-in><span class="haloed">{{ t('hero.lede') }}</span></p>
      <div class="hero__cta" data-in>
        <a class="btn btn--primary" :href="STORE_URL || '#summit'" :target="STORE_URL ? '_blank' : null" :rel="STORE_URL ? 'noopener' : null">
          <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path d="M12 3v12M7 10l5 5 5-5M5 21h14" /></svg>
          {{ STORE_URL ? t('cta.storeLive') : t('cta.store') }}
        </a>
        <a class="btn btn--ghost" href="#forecast">{{ t('cta.how') }}</a>
      </div>
    </div>

    <div class="hero__readout mono" aria-hidden="true" :style="{ transform: `translate(${readout.x}px, ${readout.y}px)`, opacity: readout.on ? 1 : 0 }">
      <span class="hero__readout-ele">{{ readout.ele }}</span>
      <span>{{ readout.pos }}</span>
    </div>

    <div ref="foot" class="hero__foot mono">
      <span class="hero__hint">{{ t('hero.hint') }}</span>
      <span class="hero__scale"><i :style="{ width: `${scale.width}px` }"></i>{{ scale.label }}</span>
      <span>{{ t('hero.contours') }}</span>
    </div>
  </section>
</template>
