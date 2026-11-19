<script setup>
// «Кольцо срока»: the check-in deadline as a dial. The scroll runs three hours down to zero —
// Pine, then Amber in the last hour, then Ember — waits out half an hour of silence and sends the alarm.
import { computed, ref } from 'vue';

import { gsap, reduced, ScrollTrigger, useMotion } from '../composables/motion.js';
import { t } from '../i18n/index.js';
import { clamp } from '../lib/format.js';
import MarkLabel from './MarkLabel.vue';
import RollingNumber from './RollingNumber.vue';

const WINDOW = 3 * 3600; // the outing: three hours to the deadline
const GRACE = 30 * 60; // then half an hour before the contacts hear of it
const R = 168;
const C = 2 * Math.PI * R;
const ticks = Array.from({ length: 60 }, (_, i) => {
  const a = (i / 60) * Math.PI * 2 - Math.PI / 2;
  const inner = i % 5 === 0 ? 180 : 186;
  return { x1: 200 + Math.cos(a) * inner, y1: 200 + Math.sin(a) * inner, x2: 200 + Math.cos(a) * 192, y2: 200 + Math.sin(a) * 192, major: i % 5 === 0 };
});

const q = ref(0);
const two = (n) => String(Math.floor(n)).padStart(2, '0');
const dial = computed(() => {
  if (q.value <= 0.55) {
    const left = WINDOW * (1 - q.value / 0.55);
    return {
      phase: 0, fraction: left / WINDOW, label: t('dial.left'), sub: t('dial.due'),
      time: `${Math.floor(left / 3600)}:${two((left % 3600) / 60)}:${two(left % 60)}`,
      color: left > 3600 ? '#05716C' : left > 900 ? '#C27F12' : '#B8322D',
    };
  }
  const over = GRACE * clamp((q.value - 0.55) / 0.27);
  const sent = q.value > 0.82;
  return {
    phase: sent ? 2 : 1, fraction: over / GRACE, label: t(sent ? 'dial.alarm' : 'dial.over'), sub: t(sent ? 'dial.contacts' : 'dial.due'),
    time: `+${two(over / 60)}:${two(over % 60)}`, color: '#B8322D',
  };
});
const steps = t('sf.steps');

const pin = ref(null);
const morse = ref(null);

useMotion(() => {
  ScrollTrigger.create({
    trigger: pin.value, start: 'top top', end: '+=200%', pin: true, scrub: true,
    onUpdate: (self) => (q.value = clamp((self.progress - 0.04) / 0.86)),
  });

  if (reduced) return;
  // · · · — — — · · ·
  const lights = morse.value.children;
  const signal = gsap.timeline({ repeat: -1, repeatDelay: 1.1, paused: true });
  [...lights].forEach((light) => {
    const long = light.classList.contains('dash');
    signal.to(light, { opacity: 1, duration: 0.06 }).to(light, { opacity: 0.18, duration: 0.14 }, `+=${long ? 0.42 : 0.14}`);
  });
  ScrollTrigger.create({ trigger: morse.value, start: 'top bottom', end: 'bottom top', onToggle: (self) => (self.isActive ? signal.play() : signal.pause()) });
});
</script>

<template>
  <section id="safety" class="safety" data-theme="light">
    <div ref="pin" class="safety__pin">
      <div class="wrap safety__grid">
        <div class="safety__copy">
          <MarkLabel :name="t('sf.label')" />
          <h2 v-split class="title">{{ t('sf.title') }}</h2>
          <p v-reveal class="text">{{ t('sf.text') }}</p>
          <ol class="timeline">
            <li v-for="(item, i) in steps" :key="i" :class="{ 'is-on': i <= dial.phase }">
              <i></i><b>{{ item[0] }}</b><span>{{ item[1] }}</span>
            </li>
          </ol>
        </div>

        <div class="dial" :style="{ '--dial': dial.color }">
          <svg class="dial__svg" viewBox="0 0 400 400" aria-hidden="true">
            <line
              v-for="(tick, i) in ticks" :key="i" :x1="tick.x1" :y1="tick.y1" :x2="tick.x2" :y2="tick.y2"
              :stroke="tick.major ? '#031163' : '#9AA6C4'" :stroke-width="tick.major ? 1.5 : 1"
            />
            <circle cx="200" cy="200" :r="R" fill="none" stroke="#D6E2E2" stroke-width="1" />
            <circle
              cx="200" cy="200" :r="R" fill="none" :stroke="dial.color" stroke-width="7" transform="rotate(-90 200 200)"
              :stroke-dasharray="C" :stroke-dashoffset="C * (1 - dial.fraction)"
            />
          </svg>
          <div class="dial__center">
            <span class="dial__label mono">{{ dial.label }}</span>
            <span class="dial__time mono"><RollingNumber :value="dial.time" /></span>
            <span class="dial__sub mono">{{ dial.sub }}</span>
          </div>
          <div class="alert" :class="{ 'is-on': dial.phase === 2 }">
            <span class="alert__tag mono">{{ t('sf.alertTag') }}</span>
            <p>{{ t('sf.alert') }}</p>
            <p class="mono alert__pos">41.49513, 70.05862 · 3 268 {{ t('unit.m') }} · 17:42 · ±12 {{ t('unit.m') }}</p>
          </div>
        </div>
      </div>
    </div>

    <div class="sos">
      <div class="wrap sos__grid">
        <div class="sos__sign" aria-hidden="true">
          <span class="sos__word">SOS</span>
          <span ref="morse" class="sos__morse"><i></i><i></i><i></i><i class="dash"></i><i class="dash"></i><i class="dash"></i><i></i><i></i><i></i></span>
        </div>
        <div class="sos__copy">
          <h3 v-split class="subtitle">{{ t('sos.title') }}</h3>
          <ul v-reveal class="plain">
            <li v-for="item in t('sos.list')" :key="item">{{ item }}</li>
          </ul>
          <p v-reveal class="sos__free">{{ t('sos.free') }}</p>
        </div>
      </div>
    </div>
  </section>
</template>
