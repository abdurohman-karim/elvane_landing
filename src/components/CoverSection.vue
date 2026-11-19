<script setup>
// Coverage: the numbers are counted from the region packs the app ships (scripts/build-data.py).
import { reactive, ref } from 'vue';

import { gsap, reduced, useMotion } from '../composables/motion.js';
import regionsData from '../data/regions.json';
import stats from '../data/stats.json';
import { lang, t } from '../i18n/index.js';
import { num } from '../lib/format.js';
import MarkLabel from './MarkLabel.vue';

const captions = t('cv.figures');
const figures = reactive([regionsData.length, stats.pathsKm, stats.springs, 72].map((value, i) => ({ value, shown: reduced ? value : 0, caption: captions[i] })));

/** A region's outline, north up, fitted into its little frame. */
const regions = regionsData.map((region) => {
  const lons = region.polygon.map((p) => p[0]);
  const lats = region.polygon.map((p) => p[1]);
  const [w, e, s, n] = [Math.min(...lons), Math.max(...lons), Math.min(...lats), Math.max(...lats)];
  const k = Math.cos((((s + n) / 2) * Math.PI) / 180);
  const scale = Math.min(44 / ((e - w) * k), 32 / (n - s));
  const ox = (44 - (e - w) * k * scale) / 2;
  const oy = (32 - (n - s) * scale) / 2;
  return {
    id: region.id, name: region.name[lang], areas: region.areas[lang], mb: Math.round(region.mb),
    points: region.polygon.map(([lon, lat]) => `${(ox + (lon - w) * k * scale).toFixed(1)},${(oy + (n - lat) * scale).toFixed(1)}`).join(' '),
  };
});

const grid = ref(null);
const list = ref(null);

useMotion(() => {
  if (reduced) return;
  figures.forEach((figure, i) => {
    gsap.to(figure, { shown: figure.value, duration: 1.8, delay: i * 0.12, ease: 'power3.out', scrollTrigger: { trigger: grid.value, start: 'top 82%', once: true } });
  });
  gsap.from(list.value.children, { y: 22, opacity: 0, duration: 0.8, stagger: 0.06, scrollTrigger: { trigger: list.value, start: 'top 86%', once: true } });
});
</script>

<template>
  <section id="cover" class="cover" data-theme="light">
    <div class="wrap">
      <MarkLabel :name="t('cv.label')" />
      <h2 v-split class="title">{{ t('cv.title') }}</h2>
      <div class="cover__grid">
        <dl ref="grid" class="figures">
          <div v-for="figure in figures" :key="figure.caption">
            <dd class="mono">{{ num(figure.shown) }}</dd>
            <dt>{{ figure.caption }}</dt>
          </div>
        </dl>
        <ul ref="list" class="regions">
          <li v-for="region in regions" :key="region.id">
            <svg viewBox="0 0 44 32" aria-hidden="true"><polygon :points="region.points" /></svg>
            <div><b>{{ region.name }}</b><span>{{ region.areas }}</span></div>
            <i>{{ region.mb }} {{ t('unit.mb') }}</i>
          </li>
        </ul>
      </div>
    </div>
  </section>
</template>
