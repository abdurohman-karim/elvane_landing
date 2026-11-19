// A contour map on a canvas: relief shading, hypsometric tints, 20 m lines. The hero and the route
// section both draw the same mountain, in the light and the dark map style of the app.

export const THEMES = {
  light: {
    bg: '#F3F7F7',
    tint: 'rgba(25, 120, 165, 0.034)',
    minorLow: 'rgba(5, 113, 108, 0.26)',
    majorLow: 'rgba(5, 113, 108, 0.58)',
    minorHigh: 'rgba(25, 120, 165, 0.34)',
    majorHigh: 'rgba(25, 120, 165, 0.7)',
    hill: { shadow: [3, 17, 99], light: [255, 255, 255], shadowAlpha: 0.2, lightAlpha: 0.55 },
  },
  dark: {
    bg: '#020A2E',
    tint: 'rgba(28, 44, 99, 0.2)',
    minorLow: 'rgba(95, 183, 224, 0.13)',
    majorLow: 'rgba(95, 183, 224, 0.3)',
    minorHigh: 'rgba(169, 188, 214, 0.2)',
    majorHigh: 'rgba(169, 188, 214, 0.42)',
    hill: { shadow: [1, 5, 26], light: [95, 183, 224], shadowAlpha: 0.6, lightAlpha: 0.1 },
  },
};

export class TopoMap {
  constructor(canvas, terrain, theme = 'light') {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d', { alpha: false });
    this.terrain = terrain;
    this.theme = THEMES[theme];
    this.hill = terrain.hillshade(this.theme.hill);
    this.view = { x: terrain.w / 2, y: terrain.h / 2, ax: 0.5, ay: 0.5, zoom: 1 };
    this.reveal = 1; // 0…1: contours fill the mountain from the bottom up
    this.layers = []; // (ctx, map) => void, drawn in map space above the contours
    this.onDraw = null;
    this.dirty = true;
    this.resize();
  }

  resize() {
    const rect = this.canvas.getBoundingClientRect();
    this.dpr = Math.min(window.devicePixelRatio || 1, rect.width > 900 ? 2 : 2.5);
    this.W = Math.max(1, Math.round(rect.width));
    this.H = Math.max(1, Math.round(rect.height));
    this.canvas.width = Math.round(this.W * this.dpr);
    this.canvas.height = Math.round(this.H * this.dpr);
    this.dirty = true;
  }

  setView(view) {
    Object.assign(this.view, view);
    this.dirty = true;
  }

  /** Scale and offset of map space on the canvas: the map always covers it. */
  frame() {
    const { w, h } = this.terrain;
    const scale = Math.max(this.W / w, this.H / h) * this.view.zoom;
    let tx = this.view.ax * this.W - this.view.x * scale;
    let ty = this.view.ay * this.H - this.view.y * scale;
    tx = Math.min(0, Math.max(this.W - w * scale, tx));
    ty = Math.min(0, Math.max(this.H - h * scale, ty));
    return { scale, tx, ty };
  }

  project(x, y) {
    const f = this.frame();
    return [x * f.scale + f.tx, y * f.scale + f.ty];
  }

  unproject(px, py) {
    const f = this.frame();
    return [(px - f.tx) / f.scale, (py - f.ty) / f.scale];
  }

  draw(force = false) {
    if (!this.dirty && !force) return;
    this.dirty = false;
    const { ctx, terrain, theme, dpr } = this;
    const f = this.frame();
    this.f = f;
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.fillStyle = theme.bg;
    ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
    ctx.setTransform(dpr * f.scale, 0, 0, dpr * f.scale, dpr * f.tx, dpr * f.ty);

    const top = terrain.min + (terrain.max - terrain.min) * this.reveal;
    const all = this.reveal >= 1;

    ctx.fillStyle = theme.tint;
    for (const l of terrain.levels) if (l.fill && l.level <= top) ctx.fill(l.fill);

    ctx.globalAlpha = Math.min(1, this.reveal * 1.4);
    ctx.imageSmoothingEnabled = true;
    ctx.imageSmoothingQuality = 'high';
    ctx.drawImage(this.hill, 0.5, 0.5, terrain.w - 1, terrain.h - 1);
    ctx.globalAlpha = 1;

    const minor = 0.75 / f.scale;
    const major = 1.3 / f.scale;
    ctx.lineJoin = 'round';
    if (all) {
      for (const [key, width] of [['minorLow', minor], ['minorHigh', minor], ['majorLow', major], ['majorHigh', major]]) {
        ctx.lineWidth = width;
        ctx.strokeStyle = theme[key];
        ctx.stroke(terrain.layers[key]);
      }
    } else {
      for (const l of terrain.levels) {
        if (l.level > top) break;
        ctx.lineWidth = l.major ? major : minor;
        ctx.strokeStyle = theme[(l.major ? 'major' : 'minor') + (l.high ? 'High' : 'Low')];
        ctx.stroke(l.stroke);
      }
    }

    for (const layer of this.layers) layer(ctx, this, f);
    this.onDraw?.(this, f);
  }
}
