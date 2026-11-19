<script setup>
// The altimeter on the left edge: a tape of heights that runs under a fixed needle as the page climbs.
import { computed } from 'vue';

import { altitude } from '../composables/altitude.js';
import { SUMMIT, TRAILHEAD } from '../config.js';

const PX_PER_M = 1.4;
const ticks = [];
for (let z = Math.ceil((TRAILHEAD - 420) / 20) * 20; z <= SUMMIT + 420; z += 20) ticks.push(z);

const offset = computed(() => `translate3d(0, ${(altitude.value * PX_PER_M).toFixed(1)}px, 0)`);
</script>

<template>
  <aside class="rail" aria-hidden="true">
    <div class="rail__tape" :style="{ transform: offset }">
      <template v-for="z in ticks" :key="z">
        <i class="rail__tick" :class="{ 'rail__tick--major': z % 100 === 0 }" :style="{ top: `${-z * PX_PER_M}px` }"></i>
        <span v-if="z % 100 === 0" class="rail__num" :style="{ top: `${-z * PX_PER_M}px` }">{{ z }}</span>
      </template>
    </div>
    <div class="rail__needle"><span class="rail__value mono">{{ Math.round(altitude) }}</span></div>
  </aside>
</template>
