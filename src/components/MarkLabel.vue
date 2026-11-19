<script setup>
// «Отметка 2 150 м · Прогноз»: every section is a mark on the way up, at the height its top scrolls to.
import { onBeforeUnmount, onMounted, ref } from 'vue';

import { altitudeAt } from '../composables/altitude.js';
import { ScrollTrigger } from '../composables/motion.js';
import { t } from '../i18n/index.js';
import { num } from '../lib/format.js';

defineProps({ name: { type: String, required: true } });

const el = ref(null);
const height = ref(0);
let probe;
const stamp = () => (height.value = altitudeAt(probe.start));

onMounted(() => {
  probe = ScrollTrigger.create({ trigger: el.value.closest('section'), start: 'top top' });
  ScrollTrigger.addEventListener('refresh', stamp);
});
onBeforeUnmount(() => {
  ScrollTrigger.removeEventListener('refresh', stamp);
  probe?.kill();
});
</script>

<template>
  <p ref="el" class="mark-label mono"><b>{{ t('mark') }} {{ num(height) }} {{ t('unit.m') }}</b><span>· {{ name }}</span></p>
</template>
