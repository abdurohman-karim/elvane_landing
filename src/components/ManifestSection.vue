<script setup>
// The manifest lights up word by word as it is read; then the things Elvane replaces are struck out.
import { ref } from 'vue';

import { gsap, reduced, ScrollTrigger, useMotion } from '../composables/motion.js';
import { t } from '../i18n/index.js';
import MarkLabel from './MarkLabel.vue';

const words = t('why.text').split(/\s+/);
const replaced = t('why.list');

const text = ref(null);
const list = ref(null);
const lit = ref(reduced ? words.length : 0);
const struck = ref(reduced ? replaced.length : 0);

useMotion(() => {
  if (reduced) return;
  ScrollTrigger.create({
    trigger: text.value, start: 'top 82%', end: 'bottom 46%', scrub: true,
    onUpdate: (self) => (lit.value = Math.round(self.progress * words.length)),
  });

  const items = list.value.querySelectorAll('li');
  const timeline = gsap.timeline({
    scrollTrigger: { trigger: list.value, start: 'top 78%', end: 'bottom 52%', scrub: 0.4 },
    onUpdate: () => (struck.value = Math.floor((timeline.time() + 0.3) / 0.8)),
  });
  items.forEach((li, i) => timeline.to(li, { '--strike': 1, duration: 1, ease: 'power2.inOut' }, i * 0.8));
});
</script>

<template>
  <section id="why" class="manifest" data-theme="light">
    <div class="wrap">
      <MarkLabel :name="t('why.label')" />
      <p ref="text" class="manifest__text">
        <template v-for="(word, i) in words" :key="i"><span class="w" :class="{ 'is-lit': i < lit }">{{ word }}</span>{{ ' ' }}</template>
      </p>

      <div class="replace">
        <p class="replace__label mono">{{ t('why.replaces') }}</p>
        <ul ref="list" class="replace__list">
          <li v-for="(item, i) in replaced" :key="item" :class="{ 'is-struck': i < struck }" :style="reduced ? { '--strike': 1 } : null">
            <span>{{ item }}</span>
          </li>
        </ul>
      </div>
    </div>
  </section>
</template>
