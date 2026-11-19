<script setup>
// «Перекат цифр»: a number changes like a mechanical counter instead of blinking.
import { computed } from 'vue';

const props = defineProps({ value: { type: String, required: true } });
const chars = computed(() => [...props.value]);
const isDigit = (ch) => ch >= '0' && ch <= '9';
</script>

<template>
  <span class="roller" :aria-label="value"><template v-for="(ch, i) in chars" :key="i"><span v-if="isDigit(ch)" class="roll" aria-hidden="true"><span class="roll__strip" :style="{ transform: `translateY(${-10 * Number(ch)}%)` }"><i v-for="d in 10" :key="d">{{ d - 1 }}</i></span></span><span v-else aria-hidden="true">{{ ch }}</span></template></span>
</template>
