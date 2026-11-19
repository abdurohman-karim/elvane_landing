import '@fontsource-variable/onest/index.css';
import '@fontsource-variable/martian-mono/standard.css';
import './styles/main.css';

import { createApp } from 'vue';

import App from './App.vue';
import { vReveal, vSplit } from './composables/motion.js';

createApp(App).directive('split', vSplit).directive('reveal', vReveal).mount('#app');
