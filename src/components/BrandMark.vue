<script setup>
// The mark: a summit of four altitude belts (Glacier, Pine, Lake and the snow cap) under a weather vane.
defineProps({ size: { type: Number, default: 30 } });
</script>

<template>
  <svg class="mark" viewBox="0 0 120 120" :width="size" :height="size" aria-hidden="true">
    <polygon points="14,104 106,104 95.4,86 24.6,86" fill="#1FBFB8" />
    <polygon points="26.7,82.5 93.3,82.5 83.6,66 36.4,66" fill="#05716C" />
    <polygon points="38.5,62.5 81.5,62.5 71.8,46 48.2,46" fill="#1978A5" />
    <polygon points="50.3,42.5 69.7,42.5 60,26" fill="currentColor" />
    <line x1="60" y1="24" x2="60" y2="10" stroke="currentColor" stroke-width="3.5" stroke-linecap="square" />
    <line x1="44" y1="10" x2="78" y2="10" stroke="currentColor" stroke-width="3.5" stroke-linecap="square" />
    <polygon points="76,4.5 86,10 76,15.5" fill="currentColor" />
    <polygon points="34,4 46,10 34,16 38,10" fill="currentColor" />
  </svg>
</template>
