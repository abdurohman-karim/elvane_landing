// The relief of Big Chimgan: an elevation grid cut from the app's own region pack (Copernicus DEM).
// Contours are traced here, in the browser, the way the app draws them — 20 m lines, bold every 100 m.
import { contours } from 'd3-contour';

import meta from '../data/terrain.json';

const STEP = 20;
const MAJOR = 100;
const TINT = 200;

/** Map space: sample (i, j) sits at (i + .5, j + .5), which is how d3-contour lays the grid out. */
export class Terrain {
  constructor(values) {
    this.w = meta.w;
    this.h = meta.h;
    this.min = meta.min;
    this.max = meta.max;
    this.values = values;
    this.generator = contours().size([this.w, this.h]);
    this.metresPerCell = 19.96; // z12 mercator pixels at 41.5° N, resampled to the grid
    this.build();
  }

  build() {
    const first = Math.ceil((this.min + 1) / STEP) * STEP;
    const levels = [];
    for (let z = first; z < this.max; z += STEP) levels.push(z);
    this.levels = this.generator.thresholds(levels)(this.values).map((geometry) => {
      const level = geometry.value;
      return {
        level,
        major: level % MAJOR === 0,
        high: level >= 3000,
        stroke: this.strokePath(geometry),
        fill: level % TINT === 0 ? this.fillPath(geometry) : null,
      };
    });
    // Whole layers for the frames where every line is on screen: four strokes instead of ninety
    this.layers = { minorLow: new Path2D(), majorLow: new Path2D(), minorHigh: new Path2D(), majorHigh: new Path2D() };
    for (const l of this.levels) {
      this.layers[(l.major ? 'major' : 'minor') + (l.high ? 'High' : 'Low')].addPath(l.stroke);
    }
  }

  /** Lines only: the pieces that run along the edge of the grid are not contours. */
  strokePath(geometry) {
    const path = new Path2D();
    const { w, h } = this;
    const edge = (p) => p[0] <= 0.001 || p[0] >= w - 0.001 || p[1] <= 0.001 || p[1] >= h - 0.001;
    for (const polygon of geometry.coordinates) {
      for (const ring of polygon) {
        let drawing = false;
        for (let i = 0; i < ring.length - 1; i++) {
          const a = ring[i];
          const b = ring[i + 1];
          if (edge(a) && edge(b)) {
            drawing = false;
            continue;
          }
          if (!drawing) path.moveTo(a[0], a[1]);
          path.lineTo(b[0], b[1]);
          drawing = true;
        }
      }
    }
    return path;
  }

  fillPath(geometry) {
    const path = new Path2D();
    for (const polygon of geometry.coordinates) {
      for (const ring of polygon) {
        ring.forEach((p, i) => (i ? path.lineTo(p[0], p[1]) : path.moveTo(p[0], p[1])));
        path.closePath();
      }
    }
    return path;
  }

  /** The contour through one height — the line that lights up under the cursor. */
  iso(level) {
    return this.strokePath(this.generator.contour(this.values, level));
  }

  eleAt(x, y) {
    const fx = Math.min(this.w - 1.001, Math.max(0, x - 0.5));
    const fy = Math.min(this.h - 1.001, Math.max(0, y - 0.5));
    const x0 = Math.floor(fx);
    const y0 = Math.floor(fy);
    const dx = fx - x0;
    const dy = fy - y0;
    const v = this.values;
    const i = y0 * this.w + x0;
    return (v[i] * (1 - dx) + v[i + 1] * dx) * (1 - dy) + (v[i + this.w] * (1 - dx) + v[i + this.w + 1] * dx) * dy;
  }

  lonLat(x, y) {
    const m = meta.mercator;
    const px = m.x0 + ((m.x1 - m.x0) * (x - 0.5)) / (this.w - 1);
    const py = m.y0 + ((m.y1 - m.y0) * (y - 0.5)) / (this.h - 1);
    const n = 256 * 2 ** m.z;
    return [(px / n) * 360 - 180, (Math.atan(Math.sinh(Math.PI * (1 - (2 * py) / n))) * 180) / Math.PI];
  }

  /** Relief shading lit from the north-west, as a small canvas the map stretches over itself. */
  hillshade({ shadow, light, shadowAlpha, lightAlpha }) {
    const { w, h, values } = this;
    const canvas = document.createElement('canvas');
    canvas.width = w;
    canvas.height = h;
    const ctx = canvas.getContext('2d');
    const image = ctx.createImageData(w, h);
    const cell = this.metresPerCell * 2;
    const flat = Math.SQRT1_2;
    for (let j = 0; j < h; j++) {
      for (let i = 0; i < w; i++) {
        const l = values[j * w + Math.max(0, i - 1)];
        const r = values[j * w + Math.min(w - 1, i + 1)];
        const u = values[Math.max(0, j - 1) * w + i];
        const d = values[Math.min(h - 1, j + 1) * w + i];
        const nx = -(r - l) / cell;
        const ny = -(d - u) / cell;
        const len = Math.hypot(nx, ny, 1);
        const s = (-nx - ny + Math.SQRT2) / (2 * len); // light from the north-west, 45° up
        const o = (j * w + i) * 4;
        if (s < flat) {
          image.data[o] = shadow[0];
          image.data[o + 1] = shadow[1];
          image.data[o + 2] = shadow[2];
          image.data[o + 3] = Math.min(1, (flat - s) / flat) * shadowAlpha * 255;
        } else {
          image.data[o] = light[0];
          image.data[o + 1] = light[1];
          image.data[o + 2] = light[2];
          image.data[o + 3] = Math.min(1, (s - flat) / (1 - flat)) * lightAlpha * 255;
        }
      }
    }
    ctx.putImageData(image, 0, 0);
    return canvas;
  }
}

export async function loadTerrain() {
  const response = await fetch(`${import.meta.env.BASE_URL}data/terrain.bin`);
  if (!response.ok) throw new Error(`terrain.bin: ${response.status}`);
  return new Terrain(new Uint16Array(await response.arrayBuffer()));
}
