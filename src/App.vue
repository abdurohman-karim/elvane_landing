<script setup>
// Elvane landing. The page is a climb: it opens at the trailhead, every section is a mark on the way
// up, and the last one is the summit. The relief under it all is real — cut from the app's own
// region pack — and is loaded before the sections mount, behind the intro.
import { nextTick, onMounted, provide, ref, shallowRef } from 'vue';

import AltimeterRail from './components/AltimeterRail.vue';
import BrandMark from './components/BrandMark.vue';
import CoverSection from './components/CoverSection.vue';
import ForecastSection from './components/ForecastSection.vue';
import HeroSection from './components/HeroSection.vue';
import ManifestSection from './components/ManifestSection.vue';
import RouteSection from './components/RouteSection.vue';
import SafetySection from './components/SafetySection.vue';
import SiteHeader from './components/SiteHeader.vue';
import SummitSection from './components/SummitSection.vue';
import WhoSection from './components/WhoSection.vue';
import { startAltitude } from './composables/altitude.js';
import { createScroll, gsap, reduced, ScrollTrigger } from './composables/motion.js';
import { TRAILHEAD } from './config.js';
import { applyDocumentLanguage, t } from './i18n/index.js';
import { loadTerrain } from './lib/terrain.js';

const terrain = shallowRef(null);
provide('terrain', terrain);

const ready = ref(false);
const introDone = ref(false);
const intro = ref(null);
const hero = ref(null);
const counter = ref('0000');

function fonts() {
  const wait = Promise.all([
    document.fonts.load('600 48px "Onest Variable"', 'Главный tool'),
    document.fonts.load('400 17px "Onest Variable"', 'Главный tool'),
    document.fonts.load('500 16px "Martian Mono Variable"', '3 309 м'),
  ]).catch(() => {});
  return Promise.race([wait, new Promise((resolve) => setTimeout(resolve, 2500))]);
}

/** The top bar and the rail take the ink of the section under them. */
function watchChrome() {
  const root = document.documentElement;
  const theme = document.querySelector('meta[name="theme-color"]');
  for (const section of document.querySelectorAll('main > section')) {
    ScrollTrigger.create({
      trigger: section, start: 'top 36px', end: 'bottom 36px',
      onToggle: (self) => {
        if (!self.isActive) return;
        root.dataset.chrome = section.dataset.theme;
        theme?.setAttribute('content', getComputedStyle(section).backgroundColor);
      },
    });
  }
}

onMounted(async () => {
  applyDocumentLanguage();
  if ('scrollRestoration' in history) history.scrollRestoration = 'manual';
  window.scrollTo(0, 0);
  const lenis = createScroll();
  lenis?.stop();

  const count = { v: 0 };
  const counting = reduced
    ? null
    : gsap.to(count, {
        v: TRAILHEAD, duration: 1.5, ease: 'power2.inOut',
        onUpdate: () => (counter.value = String(Math.round(count.v)).padStart(4, '0')),
      });

  const [loaded] = await Promise.all([
    loadTerrain().catch((error) => {
      console.error(error);
      return null;
    }),
    fonts(),
  ]);
  terrain.value = loaded;
  ready.value = true;
  await nextTick();

  watchChrome();
  ScrollTrigger.sort();
  ScrollTrigger.refresh();
  startAltitude();

  if (reduced) {
    introDone.value = true;
    hero.value.show();
    return;
  }
  await counting;
  const timeline = gsap.timeline();
  timeline
    .to(intro.value, { yPercent: -100, duration: 0.95, ease: 'power4.inOut' }, 0.1)
    .add(hero.value.enter(), 0)
    .add(() => {
      introDone.value = true;
      lenis?.start();
    }, 1.1);

  let width = innerWidth;
  addEventListener('resize', () => {
    if (innerWidth === width) return; // phone address bars change the height all the time
    width = innerWidth;
    ScrollTrigger.refresh();
  });
});
</script>

<template>
  <div v-if="!introDone" ref="intro" class="intro" aria-hidden="true">
    <div class="intro__inner">
      <BrandMark :size="56" />
      <span class="intro__num mono"><span>{{ counter }}</span> {{ t('unit.m') }}</span>
    </div>
  </div>

  <SiteHeader />
  <AltimeterRail />

  <main v-if="ready">
    <HeroSection ref="hero" />
    <ManifestSection />
    <ForecastSection />
    <RouteSection />
    <SafetySection />
    <WhoSection />
    <CoverSection />
    <SummitSection />
  </main>
</template>
