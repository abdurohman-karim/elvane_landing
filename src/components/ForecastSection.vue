<script setup>
// The app's signature gesture — the altitude slider: the scroll (or a drag) leads the height along the
// real cross-section of Big Chimgan and the weather is recounted for it on the spot.
// Below it, the «лента окон»: seven days of hourly verdicts under one scrub.
import { computed, ref } from 'vue';

import { gsap, reduced, ScrollTrigger, useMotion } from '../composables/motion.js';
import { SUMMIT } from '../config.js';
import silhouette from '../data/silhouette.json';
import { lang, t } from '../i18n/index.js';
import { clamp, dec, deg, lerp, num } from '../lib/format.js';
import MarkLabel from './MarkLabel.vue';
import RollingNumber from './RollingNumber.vue';

// ── the slope ────────────────────────────────────────────────────────────────
const W = 640;
const H = 520;
const X0 = 64;
const BASE = 1700;
const ZERO = 2400; // the zero isotherm of the example day
const CEIL = SUMMIT + 60;

const raw = silhouette.ele;
const lo = Math.min(...raw);
const hi = Math.max(...raw);
// The 30 m DEM rounds the very top off; the catalog height is 3 309 m
const ele = raw.map((z) => z + (SUMMIT - hi) * ((z - lo) / (hi - lo)) ** 2);
const top = ele.indexOf(Math.max(...ele));
const xOf = (i) => X0 + (i / (ele.length - 1)) * (W - X0);
const yOf = (z) => H - 14 - ((z - 1500) / (CEIL - 1500)) * (H - 40);
const outline = ele.map((z, i) => `${i ? 'L' : 'M'}${xOf(i).toFixed(1)} ${yOf(z).toFixed(1)}`).join(' ');
const stripes = [];
for (let z = 1600; z < SUMMIT; z += 100) stripes.push(z);

const alt = ref(BASE);
const y = computed(() => yOf(alt.value));
/** Where the chosen height meets the left flank of the mountain. */
const x = computed(() => {
  for (let i = 1; i <= top; i++) {
    if (ele[i] >= alt.value) {
      const a = ele[i - 1];
      return a >= alt.value ? xOf(i - 1) : lerp(xOf(i - 1), xOf(i), (alt.value - a) / (ele[i] - a));
    }
  }
  return xOf(top);
});

/** The example day of the app's mockups: lapse rate, wind growing with height, wind chill, UV. */
const weather = computed(() => {
  const z = alt.value;
  const temp = 5.2 - 0.0065 * (z - 1600);
  const wind = 3 + ((z - 1600) / 1709) * 9;
  const kmh = wind * 3.6;
  const feels = temp <= 10 && kmh > 4.8 ? 13.12 + 0.6215 * temp - 11.37 * kmh ** 0.16 + 0.3965 * temp * kmh ** 0.16 : temp;
  return {
    alt: num(z >= SUMMIT - 4 ? SUMMIT : Math.round(z / 10) * 10),
    temp: deg(temp),
    feels: deg(feels),
    wind: `${Math.round(wind)} ${t('unit.ms')}`,
    phase: t(temp <= 0.5 ? 'ph.snow' : temp <= 2 ? 'ph.sleet' : 'ph.rain'),
    uv: dec(2 * (1 + (0.08 * z) / 1000), lang),
  };
});

const pin = ref(null);
const svg = ref(null);
const edge = ref(null);
const dot = ref(null);
const inside = ref(null);

let hundred = Math.floor(BASE / 100);
function setAlt(z) {
  alt.value = clamp(z, BASE, SUMMIT);
  // «щелчок каждые 100 м»
  const h = Math.floor(alt.value / 100);
  if (h !== hundred && !reduced && dot.value) {
    gsap.fromTo(dot.value, { attr: { r: 10 } }, { attr: { r: 6 }, duration: 0.35, ease: 'power2.out', overwrite: true });
  }
  hundred = h;
}

// Dragging the line by hand, as in the app
let dragging = false;
function altAt(event) {
  const point = svg.value.createSVGPoint();
  point.x = event.clientX;
  point.y = event.clientY;
  const p = point.matrixTransform(svg.value.getScreenCTM().inverse());
  return 1500 + ((H - 14 - p.y) / (H - 40)) * (CEIL - 1500);
}
function onDown(event) {
  if (event.pointerType === 'touch') return; // touch scrolls the page, and the scroll moves the line
  dragging = true;
  svg.value.setPointerCapture(event.pointerId);
  setAlt(altAt(event));
}
function onDrag(event) {
  if (dragging) setAlt(altAt(event));
}
function onUp() {
  dragging = false;
}

// ── seven days, hour by hour ───────────────────────────────────────────────────
// g — good, c — caution, b — not recommended; 13 hours, 06…18
const WEEK = [
  { cells: 'gggggggcccccc', why: { g: [['g']], c: [['wind', 14]] } },
  { cells: 'ccccccccccccc', why: { c: [['wind', 14], ['cold', '−19']] } },
  { cells: 'ccccbbbbbbbbb', why: { c: [['cloud']], b: [['snow', 7], ['cloud']] } },
  { cells: 'bbbccccccgggg', why: { b: [['cloud']], c: [['cloud']], g: [['g']] } },
  { cells: 'ggggggggggggg', why: { g: [['g']] } },
  { cells: 'cgggggggggccc', why: { c: [['cloud']], g: [['g']] } },
  { cells: 'ccccgggggbbbb', why: { c: [['cold', '−27']], g: [['g']], b: [['storm', 15]] } },
];
const today = new Date();
const days = WEEK.map((day, d) => {
  const date = new Date(today.getFullYear(), today.getMonth(), today.getDate() + d);
  const weekday = (date.getDay() + 6) % 7;
  return { ...day, cells: [...day.cells], short: t('days')[weekday], name: t('daysFull')[weekday], date: date.getDate() };
});
const hot = ref(null); // { d, h }
const two = (n) => String(n).padStart(2, '0');
const note = computed(() => {
  if (!hot.value) return null;
  const day = days[hot.value.d];
  const rate = day.cells[hot.value.h];
  const reasons = day.why[rate].map(([key, v]) => t(`reason.${key}`, { v })).join(' ');
  const first = day.cells.indexOf('g');
  const best = first >= 0 && rate !== 'g' ? ' ' + t('best', { a: two(6 + first), b: two(7 + day.cells.lastIndexOf('g')) }) : '';
  return { head: `${day.name}, ${two(6 + hot.value.h)}:00 — ${t(`rate.${rate}`)}.`, body: reasons + best };
});
function onScrub(event) {
  const cell = document.elementFromPoint(event.clientX, event.clientY);
  if (cell?.dataset.h == null) return;
  hot.value = { d: Number(cell.dataset.d), h: Number(cell.dataset.h) };
}

const strip = ref(null);

useMotion(() => {
  ScrollTrigger.create({
    trigger: pin.value, start: 'top top', end: '+=170%', pin: true, scrub: true,
    onUpdate: (self) => setAlt(lerp(BASE, SUMMIT, clamp((self.progress - 0.04) / 0.82))),
  });
  if (reduced) return;
  const length = edge.value.getTotalLength();
  const once = { trigger: svg.value, start: 'top 80%', once: true };
  gsap.fromTo(edge.value, { strokeDasharray: length, strokeDashoffset: length }, { strokeDashoffset: 0, duration: 1.8, ease: 'power2.inOut', scrollTrigger: once });
  gsap.from(inside.value, { opacity: 0, duration: 1.2, delay: 0.5, scrollTrigger: { ...once } });
  gsap.from(strip.value.querySelectorAll('.day__cells i'), {
    scaleY: 0, duration: 0.7, ease: 'power3.out', stagger: 0.009,
    scrollTrigger: { trigger: strip.value, start: 'top 84%', once: true },
  });
});
</script>

<template>
  <section id="forecast" class="forecast" data-theme="dark">
    <div ref="pin" class="forecast__pin">
      <div class="wrap forecast__grid">
        <div class="forecast__copy">
          <MarkLabel :name="t('fc.label')" />
          <h2 v-split class="title">{{ t('fc.title') }}</h2>
          <p v-reveal class="text">{{ t('fc.text') }}</p>

          <dl class="readout">
            <div class="readout__main">
              <dt class="mono">{{ t('fc.at') }}</dt>
              <dd class="readout__alt mono"><RollingNumber :value="weather.alt" /> <small>{{ t('unit.m') }}</small></dd>
              <dd class="readout__temp mono"><RollingNumber :value="weather.temp" /></dd>
            </div>
            <div><dt>{{ t('fc.feels') }}</dt><dd class="mono"><RollingNumber :value="weather.feels" /></dd></div>
            <div><dt>{{ t('fc.wind') }}</dt><dd class="mono"><RollingNumber :value="weather.wind" /></dd></div>
            <div><dt>{{ t('fc.precip') }}</dt><dd>{{ weather.phase }}</dd></div>
            <div><dt>{{ t('fc.uv') }}</dt><dd class="mono"><RollingNumber :value="weather.uv" /></dd></div>
          </dl>
        </div>

        <div class="slope">
          <svg
            ref="svg" class="slope__svg" :viewBox="`0 0 ${W} ${H}`" role="img" :aria-label="t('fc.aria')"
            @pointerdown="onDown" @pointermove="onDrag" @pointerup="onUp" @pointercancel="onUp"
          >
            <defs>
              <clipPath id="slope-clip"><path :d="`${outline} L${W} ${H} L${X0} ${H} Z`" /></clipPath>
            </defs>
            <g ref="inside" clip-path="url(#slope-clip)">
              <rect x="0" y="0" :width="W" :height="yOf(3000)" fill="rgba(95,183,224,.2)" />
              <rect x="0" :y="yOf(3000)" :width="W" :height="H" fill="rgba(31,191,184,.1)" />
              <rect x="0" :y="y" :width="W" :height="H" fill="rgba(31,191,184,.26)" />
              <line
                v-for="z in stripes" :key="z" x1="0" :x2="W" :y1="yOf(z)" :y2="yOf(z)" stroke-width="1"
                :stroke="z % 500 === 0 ? 'rgba(169,188,214,.34)' : 'rgba(169,188,214,.15)'"
              />
            </g>
            <g v-for="z in [2000, 2500, 3000]" :key="z">
              <text x="0" :y="yOf(z) + 4">{{ z }}</text>
              <line x1="44" :x2="X0 - 4" :y1="yOf(z)" :y2="yOf(z)" stroke="#1C2C63" stroke-width="1" />
            </g>
            <path ref="edge" :d="outline" fill="none" stroke="#E6F2F2" stroke-width="1.5" stroke-linejoin="round" />
            <line :x1="X0" :x2="W" :y1="yOf(ZERO)" :y2="yOf(ZERO)" stroke="#5FB7E0" stroke-width="1.25" stroke-dasharray="6 4" />
            <text :x="W" :y="yOf(ZERO) - 8" text-anchor="end" style="fill: #5FB7E0">0 °C</text>
            <text :x="xOf(top)" :y="yOf(SUMMIT) - 12" text-anchor="middle" style="fill: #E6F2F2">{{ num(SUMMIT) }}</text>

            <line :x1="x" :x2="W" :y1="y" :y2="y" stroke="#1FBFB8" stroke-width="2" />
            <circle ref="dot" :cx="x" :cy="y" r="6" fill="#1FBFB8" stroke="#020A2E" stroke-width="2.5" />
            <g :transform="`translate(0 ${y})`">
              <rect :x="W - 76" y="-13" width="76" height="26" rx="4" fill="#1FBFB8" />
              <text :x="W - 38" y="4" text-anchor="middle" style="fill: #031163; font-weight: 500">{{ weather.alt }}</text>
            </g>
          </svg>
          <p class="slope__hint mono">{{ t('fc.hint') }}</p>
        </div>
      </div>
    </div>

    <div class="wrap windows">
      <div class="windows__head">
        <h3 v-split class="subtitle">{{ t('win.title') }}</h3>
        <p v-reveal class="text">{{ t('win.text') }}</p>
      </div>
      <div ref="strip" class="strip" :class="{ 'is-scrubbing': hot }">
        <div class="strip__days" @pointermove="onScrub" @pointerdown="onScrub" @pointerleave="hot = null">
          <div v-for="(day, d) in days" :key="d" class="day">
            <span class="day__name">{{ day.short }}<i>{{ day.date }}</i></span>
            <span class="day__cells">
              <i
                v-for="(rate, h) in day.cells" :key="h" :data-d="d" :data-h="h"
                :class="[rate, { 'is-hot': hot && hot.d === d && hot.h === h }]"
              ></i>
            </span>
          </div>
        </div>
        <div class="strip__hours mono" aria-hidden="true"><span>06</span><span>09</span><span>12</span><span>15</span><span>18</span></div>
        <p class="strip__note" aria-live="polite">
          <template v-if="note"><b>{{ note.head }}</b> {{ note.body }}</template>
          <template v-else><b>{{ t('win.idle') }}</b> {{ t('win.idle2') }}</template>
        </p>
        <ul class="legend mono">
          <li><i class="k-good"></i>{{ t('rate.g') }}</li>
          <li><i class="k-caution"></i>{{ t('rate.c') }}</li>
          <li><i class="k-bad"></i>{{ t('rate.b') }}</li>
        </ul>
      </div>
    </div>
  </section>
</template>
