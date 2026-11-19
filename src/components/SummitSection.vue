<script setup>
// The summit: the end of the climb. Contour rings close in around the top — the same wobbling rings
// as on the app icon — and the page hands over to the App Store and the Telegram bot.
import { onBeforeUnmount, ref } from 'vue';

import { gsap, reduced, ScrollTrigger, useMotion } from '../composables/motion.js';
import { BOT_URL, STORE_URL, SUMMIT } from '../config.js';
import { t } from '../i18n/index.js';
import { num } from '../lib/format.js';
import BrandMark from './BrandMark.vue';

const section = ref(null);
const canvas = ref(null);
const state = { grow: reduced ? 1 : 0, visible: false };
let tick = null;
let observer = null;

function draw(time) {
  const el = canvas.value;
  const ctx = el.getContext('2d');
  const dpr = Math.min(devicePixelRatio || 1, 2);
  const w = el.clientWidth;
  const h = el.clientHeight;
  if (el.width !== Math.round(w * dpr)) {
    el.width = Math.round(w * dpr);
    el.height = Math.round(h * dpr);
  }
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, w, h);
  const cx = w > 900 ? w * 0.74 : w * 0.7;
  const cy = w > 900 ? h * 0.42 : h * 0.24;
  const unit = Math.max(w, h) / 13;
  const rings = 14;
  for (let ring = 1; ring <= rings; ring++) {
    const appear = Math.min(1, Math.max(0, state.grow * rings - (rings - ring)));
    if (appear <= 0) continue;
    const radius = ring * unit * (0.86 + 0.14 * appear);
    ctx.beginPath();
    for (let step = 0; step <= 144; step++) {
      const a = (step / 144) * Math.PI * 2;
      const wobble = 1 + 0.07 * Math.sin(3 * a + ring + time * 0.11) + 0.04 * Math.cos(5 * a - ring * 0.7 - time * 0.07);
      const x = cx + Math.cos(a) * radius * wobble * 1.2;
      const y = cy + Math.sin(a) * radius * wobble;
      if (step) ctx.lineTo(x, y);
      else ctx.moveTo(x, y);
    }
    ctx.closePath();
    const major = ring % 5 === 0;
    ctx.globalAlpha = appear;
    ctx.lineWidth = major ? 1.6 : 1;
    ctx.strokeStyle = ring === 1 ? '#1FBFB8' : major ? 'rgba(95, 183, 224, 0.55)' : 'rgba(95, 183, 224, 0.24)';
    ctx.stroke();
  }
  ctx.globalAlpha = 1;
}

useMotion(() => {
  draw(0);
  ScrollTrigger.create({ trigger: section.value, start: 'top bottom', end: 'bottom top', onToggle: (self) => (state.visible = self.isActive) });
  observer = new ResizeObserver(() => draw(gsap.ticker.time));
  observer.observe(canvas.value);
  if (reduced) return;
  gsap.to(state, { grow: 1, ease: 'none', scrollTrigger: { trigger: section.value, start: 'top 85%', end: 'top 5%', scrub: true } });
  tick = (time) => state.visible && draw(time);
  gsap.ticker.add(tick);
});

onBeforeUnmount(() => {
  if (tick) gsap.ticker.remove(tick);
  observer?.disconnect();
});
</script>

<template>
  <section id="summit" ref="section" class="summit" data-theme="dark">
    <canvas ref="canvas" class="summit__canvas" aria-hidden="true"></canvas>
    <div class="wrap summit__body">
      <p class="summit__alt mono">{{ num(SUMMIT) }} {{ t('unit.m') }}</p>
      <h2 v-split class="display display--summit">{{ t('sm.title') }}</h2>
      <p v-reveal class="text">{{ t('sm.text') }}</p>
      <div v-reveal class="summit__cta">
        <a v-if="STORE_URL" class="btn btn--accent" :href="STORE_URL" target="_blank" rel="noopener">
          <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path d="M12 3v12M7 10l5 5 5-5M5 21h14" /></svg>
          {{ t('cta.storeLive') }}
        </a>
        <span v-else class="btn btn--accent btn--soon">{{ t('cta.store') }}</span>
        <a class="btn btn--line" :href="BOT_URL" target="_blank" rel="noopener">
          <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path d="M20 4 4 11l7 2 2 7 7-16Z" /></svg>
          {{ t('cta.bot') }}
        </a>
      </div>
    </div>

    <footer class="foot">
      <div class="wrap foot__grid">
        <a class="brand" href="#top" aria-label="Elvane">
          <BrandMark :size="26" />
          <span class="brand__name">elvane</span>
        </a>
        <p class="foot__note">{{ t('ft.note') }}</p>
        <p class="foot__credits mono">{{ t('ft.credits') }}</p>
        <p class="foot__copy mono">© 2026 Elvane · elvane.cloud</p>
      </div>
    </footer>
  </section>
</template>
