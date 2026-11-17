/*! SPDX-License-Identifier: Apache-2.0
 * Adapted from Spoken World, Copyright 2026 ryannli.
 * Source: app/js/core.js at 2c398a545eca4364ff6029940cecc4719c21b862.
 * Modified: isolated the pure part recorder and exported it as an ES module.
 * No world runtime, model-written code execution, browser storage or provider code.
 * See vendor/spoken-world/LICENSE and NOTICE.
 */
export function makeBuilder(seed, maxParts) {
    var count = 0, MAX = maxParts || 6000;
    var s = (seed >>> 0) || 1;
    function rnd() { s |= 0; s = (s + 0x6d2b79f5) | 0; var t = Math.imul(s ^ (s >>> 15), 1 | s); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }
    function n(v, d) { v = +v; return isFinite(v) ? v : d; }
    var OKEYS = ['rx', 'ry', 'rz', 'sx', 'sy', 'sz', 's', 'emissive', 'glow', 'metal', 'rough', 'opacity', 'flat', 'tex', 'sides', 'seg', 'noShadow', 'unlit', 'bg', 'glowK', 'grad'];
    function opts(o) {
      if (!o || typeof o !== 'object') return undefined;
      var r = {}, any = false;
      for (var i = 0; i < OKEYS.length; i++) { var k = OKEYS[i], v = o[k]; if (v === undefined || v === null) continue; var t = typeof v; if (t === 'number' || t === 'string' || t === 'boolean') { r[k] = v; any = true; } }
      return any ? r : undefined;
    }
    function pairs(arr, dim) {
      var out = [];
      if (!arr || typeof arr.length !== 'number') return out;
      for (var i = 0; i < arr.length && i < 400; i++) { var p = arr[i]; if (!p) continue; var q = []; for (var j = 0; j < dim; j++) q.push(n(p[j], 0)); out.push(q); }
      return out;
    }
    var root = { k: 'g', ch: [] }, cur = root, anchors = {};
    function part(k, a, c, x, y, z, o) {
      if (++count > MAX) throw new Error('too many parts (>' + MAX + ')');
      var p = { k: k, a: a, c: c === undefined || c === null ? '#cccccc' : (typeof c === 'number' || typeof c === 'string' ? c : '#cccccc'), t: [n(x, 0), n(y, 0), n(z, 0)] };
      var oo = opts(o); if (oo) p.o = oo;
      cur.ch.push(p);
      return p;
    }
    var b = {
      box: function (w, h, d, c, x, y, z, o) { return part('box', [n(w, 1), n(h, 1), n(d, 1)], c, x, y, z, o); },
      cyl: function (rt, rb, h, c, x, y, z, o) { return part('cyl', [n(rt, 0.5), n(rb, 0.5), n(h, 1)], c, x, y, z, o); },
      cone: function (r, h, c, x, y, z, o) { return part('cone', [n(r, 0.5), n(h, 1)], c, x, y, z, o); },
      sphere: function (r, c, x, y, z, o) { return part('sph', [n(r, 0.5)], c, x, y, z, o); },
      foliage: function (r, c, x, y, z, o) { return part('fol', [n(r, 0.5)], c, x, y, z, o); },
      puff: function (r, c, x, y, z, o) { return part('puf', [n(r, 0.5)], c, x, y, z, o); }, // a soft billow: cloud, smoke, steam, snow drift — lit above, in shade beneath // a mass of leaves: a lumpy, soft-shaded crown, lighter above and darker beneath, with leaves breaking its outline
      roof: function (w, h, d, c, x, y, z, o) { return part('roof', [n(w, 1), n(h, 1), n(d, 1)], c, x, y, z, o); },
      pyramid: function (w, h, d, c, x, y, z, o) { return part('pyr', [n(w, 1), n(h, 1), n(d, 1)], c, x, y, z, o); },
      torus: function (R, r, c, x, y, z, o) { return part('tor', [n(R, 1), n(r, 0.2)], c, x, y, z, o); },
      lathe: function (pts, c, x, y, z, o) { return part('lathe', [pairs(pts, 2)], c, x, y, z, o); },
      extrude: function (pts, depth, c, x, y, z, o) { return part('ext', [pairs(pts, 2), n(depth, 1)], c, x, y, z, o); },
      tube: function (pts, r, c, o) { return part('tube', [pairs(pts, 3), n(r, 0.05)], c, 0, 0, 0, o); },
      text: function (str, size, c, x, y, z, o) { return part('text', [String(str === undefined ? '' : str).slice(0, 40), n(size, 0.5)], c, x, y, z, o); },
      halo: function (size, c, x, y, z) { return part('halo', [n(size, 2)], c, x, y, z); },
      group: function (tf, fn) {
        if (typeof tf === 'function') { fn = tf; tf = {}; }
        var t = {};
        if (tf && typeof tf === 'object') {
          var ks = ['x', 'y', 'z', 'rx', 'ry', 'rz', 'scale', 'sx', 'sy', 'sz'];
          for (var i = 0; i < ks.length; i++) if (tf[ks[i]] !== undefined) t[ks[i]] = n(tf[ks[i]], ks[i][0] === 's' ? 1 : 0);
          if (tf.anim && typeof tf.anim === 'object') { try { t.anim = JSON.parse(JSON.stringify(tf.anim)); } catch (e) {} }
        }
        var g = { k: 'g', tf: t, ch: [] };
        if (++count > MAX) throw new Error('too many parts');
        cur.ch.push(g);
        var prev = cur; cur = g;
        try { if (typeof fn === 'function') fn(); } finally { cur = prev; }
        return g;
      },
      anchor: function (name, x, y, z, ry) { anchors[String(name)] = ry == null ? [n(x, 0), n(y, 0), n(z, 0)] : [n(x, 0), n(y, 0), n(z, 0), (n(ry, 0) * Math.PI) / 180]; }, // ry (degrees): which way someone sitting there faces
      rand: rnd,
    };
    b.cylinder = b.cyl; b.cube = b.box; b.ball = b.sphere; b.ring = b.torus; b.prism = b.roof; b.label = b.text;
    b.capsule = function (r, h, c, x, y, z, o) { r = n(r, 0.3); h = Math.max(n(h, 1), r * 2); var g = b.group({ x: n(x, 0), y: n(y, 0), z: n(z, 0), rx: o && o.rx, ry: o && o.ry, rz: o && o.rz }, function () { var oo = {}; if (o) for (var k in o) if (k !== 'rx' && k !== 'ry' && k !== 'rz') oo[k] = o[k]; b.cyl(r, r, h - 2 * r, c, 0, r, 0, oo); b.sphere(r, c, 0, r, 0, oo); b.sphere(r, c, 0, h - r, 0, oo); }); return g; };
    return { b: b, root: root, anchors: anchors, rnd: rnd };
  }
