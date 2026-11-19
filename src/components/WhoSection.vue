<script setup>
// Who it is for: a walk sideways. On a wide screen the scroll carries a row of panels — climbers,
// hikers, anglers, hunters, skiers — each under a cartographic sign from the app's own icon set.
import { ref } from 'vue';

import { gsap, reduced, ScrollTrigger, useMotion } from '../composables/motion.js';
import { t } from '../i18n/index.js';
import MarkLabel from './MarkLabel.vue';

// The signs are drawn on the app's 24 pt grid (Packages/DesignSystem/Icons.swift)
const GLYPHS = {
  climb: 'M2 20 9 7l4 7 3-4.500L22 20Z',
  hike: 'M3 20 12 5l9 15ZM12 5v15',
  fish: 'M12 5c3 4 5 6 5 9a5 5 0 0 1-10 0c0-3 2-5 5-9Z',
  hunt: 'M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0ZM12 5l2.600 7L12 19l-2.600-7Z',
  ski: 'M12 3v18M4.200 7.500l15.600 9M19.800 7.500l-15.600 9M9 4.500l3 2 3-2M9 19.500l3-2 3 2',
};
const groups = t('who.panels');
const panels = Object.keys(GLYPHS).map((id) => ({ id, glyph: GLYPHS[id], ...groups[id] }));

const pin = ref(null);
const track = ref(null);

useMotion(() => {
  const media = gsap.matchMedia();
  media.add('(min-width: 901px)', () => {
    const distance = () => track.value.scrollWidth - innerWidth;
    const walk = gsap.to(track.value, {
      x: () => -distance(), ease: 'none',
      scrollTrigger: { trigger: pin.value, start: 'top top', end: () => `+=${distance()}`, pin: true, scrub: true, invalidateOnRefresh: true },
    });
    if (reduced) return;
    for (const panel of track.value.querySelectorAll('.who__panel[data-who]')) {
      const sign = panel.querySelector('.who__glyph path');
      const length = sign.getTotalLength();
      const inView = { trigger: panel, containerAnimation: walk, start: 'left 78%', toggleActions: 'play none none reverse' };
      gsap.fromTo(sign, { strokeDasharray: length, strokeDashoffset: length }, { strokeDashoffset: 0, duration: 1.6, ease: 'power2.inOut', scrollTrigger: inView });
      gsap.from(panel.querySelector('.who__name'), { xPercent: 22, ease: 'none', scrollTrigger: { trigger: panel, containerAnimation: walk, start: 'left right', end: 'left 30%', scrub: true } });
      gsap.from(panel.querySelectorAll('.who__claim, .who__list li'), { y: 26, opacity: 0, duration: 0.8, stagger: 0.07, scrollTrigger: { ...inView, start: 'left 62%' } });
    }
  });
  media.add('(max-width: 900px)', () => {
    if (reduced) return;
    for (const panel of track.value.querySelectorAll('.who__panel[data-who]')) {
      const sign = panel.querySelector('.who__glyph path');
      const length = sign.getTotalLength();
      const once = { trigger: panel, start: 'top 78%', once: true };
      gsap.fromTo(sign, { strokeDasharray: length, strokeDashoffset: length }, { strokeDashoffset: 0, duration: 1.4, ease: 'power2.inOut', scrollTrigger: once });
      gsap.from(panel.querySelectorAll('.who__name, .who__claim, .who__list li'), { y: 26, opacity: 0, duration: 0.8, stagger: 0.07, scrollTrigger: { ...once } });
    }
  });
});
</script>

<template>
  <section id="who" class="who" data-theme="pine">
    <div ref="pin" class="who__pin">
      <div ref="track" class="who__track">
        <article class="who__panel who__panel--intro">
          <MarkLabel :name="t('who.label')" />
          <h2 class="title">{{ t('who.title') }}</h2>
          <p class="text">{{ t('who.text') }}</p>
          <span class="who__go mono">
            {{ t('who.scroll') }}
            <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path d="M4 12h16M14 6l6 6-6 6" /></svg>
          </span>
        </article>

        <article v-for="panel in panels" :key="panel.id" class="who__panel" :data-who="panel.id">
          <svg class="who__glyph" viewBox="0 0 24 24" aria-hidden="true"><path :d="panel.glyph" /></svg>
          <h3 class="who__name">{{ panel.name }}</h3>
          <p class="who__claim">{{ panel.claim }}</p>
          <ul class="who__list">
            <li v-for="item in panel.list" :key="item">{{ item }}</li>
          </ul>
        </article>
      </div>
    </div>
  </section>
</template>
