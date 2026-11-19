// GSAP, ScrollTrigger and Lenis for the whole page, and the two entrances every section shares:
// v-split (a headline rises line by line out of its mask) and v-reveal (a block fades up).
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { SplitText } from 'gsap/SplitText';
import Lenis from 'lenis';
import { onBeforeUnmount, onMounted } from 'vue';

gsap.registerPlugin(ScrollTrigger, SplitText);
gsap.defaults({ ease: 'power3.out' });

export { gsap, ScrollTrigger, SplitText };

export const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;

let lenis = null;

export function createScroll() {
  if (reduced || lenis) return lenis;
  lenis = new Lenis({ lerp: 0.1, anchors: true });
  lenis.on('scroll', ScrollTrigger.update);
  gsap.ticker.add((time) => lenis.raf(time * 1000));
  gsap.ticker.lagSmoothing(0);
  return lenis;
}

/** Runs the component's animations in a gsap.context once it is mounted and reverts them with it. */
export function useMotion(setup) {
  let context;
  onMounted(() => {
    context = gsap.context(setup);
  });
  onBeforeUnmount(() => context?.revert());
}

export const vSplit = {
  mounted(el) {
    const split = new SplitText(el, { type: 'lines', mask: 'lines', linesClass: 'split-line', autoSplit: true });
    el._split = split;
    el._tween = gsap.from(split.lines, {
      yPercent: 108, duration: reduced ? 0 : 1.1, stagger: 0.09, ease: 'power4.out',
      scrollTrigger: { trigger: el, start: 'top 86%', once: true },
    });
  },
  unmounted(el) {
    el._tween?.scrollTrigger?.kill();
    el._tween?.kill();
    el._split?.revert();
  },
};

export const vReveal = {
  mounted(el) {
    el._tween = gsap.from(el, {
      y: 28, opacity: 0, duration: reduced ? 0 : 1,
      scrollTrigger: { trigger: el, start: 'top 90%', once: true },
    });
  },
  unmounted(el) {
    el._tween?.scrollTrigger?.kill();
    el._tween?.kill();
  },
};
