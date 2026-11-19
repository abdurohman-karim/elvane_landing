// The page is one climb: scrolling from the top to the bottom goes from the trailhead (1 717 m)
// to the summit of Big Chimgan (3 309 m). Every component reads the same height.
import { ref } from 'vue';

import { SUMMIT, TRAILHEAD } from '../config.js';
import { gsap, ScrollTrigger } from './motion.js';

export const altitude = ref(TRAILHEAD);

export function altitudeAt(scroll) {
  const max = ScrollTrigger.maxScroll(window) || 1;
  return TRAILHEAD + (SUMMIT - TRAILHEAD) * Math.min(1, Math.max(0, scroll / max));
}

let started = false;
export function startAltitude() {
  if (started) return;
  started = true;
  gsap.ticker.add(() => {
    const z = altitudeAt(window.scrollY);
    if (Math.abs(z - altitude.value) > 0.05) altitude.value = z;
  });
}
