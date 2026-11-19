<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';

import { altitude } from '../composables/altitude.js';
import { ScrollTrigger } from '../composables/motion.js';
import { other, switchLanguage, t } from '../i18n/index.js';
import { band, num } from '../lib/format.js';
import BrandMark from './BrandMark.vue';

const metres = computed(() => Math.round(altitude.value));

// The bar steps aside on the way down and comes back, on the section's own paper, on the way up
const hidden = ref(false);
const solid = ref(false);
let watcher;
onMounted(() => {
  watcher = ScrollTrigger.create({
    start: 0, end: 'max',
    onUpdate: (self) => {
      const y = self.scroll();
      solid.value = y > 80;
      if (y < 160) hidden.value = false;
      else if (Math.abs(self.getVelocity()) > 40) hidden.value = self.direction > 0;
    },
  });
});
onBeforeUnmount(() => watcher?.kill());
</script>

<template>
  <header class="top" :class="{ 'is-hidden': hidden, 'is-solid': solid }">
    <a class="brand" href="#top" aria-label="Elvane">
      <BrandMark :size="30" />
      <span class="brand__name">elvane</span>
    </a>
    <nav class="top__nav" :aria-label="t('nav.aria')">
      <a href="#forecast">{{ t('nav.forecast') }}</a>
      <a href="#map">{{ t('nav.map') }}</a>
      <a href="#safety">{{ t('nav.safety') }}</a>
      <a href="#who">{{ t('nav.who') }}</a>
    </nav>
    <div class="top__side">
      <span class="alt-chip mono" aria-hidden="true">
        <i class="alt-chip__band" :style="{ background: band(metres) }"></i>{{ num(metres) }} {{ t('unit.m') }}
      </span>
      <button class="lang mono" type="button" :aria-label="t('lang.switch')" @click="switchLanguage">{{ other.toUpperCase() }}</button>
      <a class="btn btn--small" href="#summit">{{ t('nav.get') }}</a>
    </div>
  </header>
</template>
