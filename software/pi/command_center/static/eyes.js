/* The LCD page. It owns all animation timing; the server only names an
   animation and pushes calibration. Nothing here talks back. */
(function () {
  "use strict";

  var data = JSON.parse(document.getElementById("eyes-data").textContent);
  var stage = document.getElementById("stage");
  var fit = document.getElementById("fit");
  var eyes = document.querySelectorAll(".eye");   // [left, right]
  var lid = document.getElementById("lid");
  var offline = document.getElementById("offline");

  var bboxW = data.bbox[2], bboxH = data.bbox[3];
  var centerX = data.center[0], centerY = data.center[1];
  // Far enough above the face that the lid is completely clear of it at rest.
  var LID_PARK = -(bboxH + 20);
  // Timing comes from eyes/animations.py. The fallback matters: the static
  // files and the Python are deployed together but restart separately, so a
  // server that has not been restarted yet serves this newer script without
  // the timing. Without a default, every blink then throws instead of playing.
  var BLINK = data.blink || { ms: 500, closedFrom: 0.32, closedTo: 0.62 };

  var calibration = data.calibration;

  /* ---- placing the face on the panel ---------------------------------- */

  // The SVG's user units are panel pixels, so one transform does everything:
  // move the contour's centre to the middle of the screen, scale it to fit,
  // then apply the operator's calibration on top.
  function applyFit() {
    var w = window.innerWidth, h = window.innerHeight;
    stage.setAttribute("viewBox", "0 0 " + w + " " + h);
    var k = Math.min(w / bboxW, h / bboxH);   // largest size that still fits
    fit.setAttribute("transform",
      "translate(" + (w / 2 + calibration.offset_x) + " " +
                     (h / 2 + calibration.offset_y) + ") " +
      "scale(" + (k * calibration.scale_x) + " " +
                 (k * calibration.scale_y) + ") " +
      "translate(" + (-centerX) + " " + (-centerY) + ")");
  }

  /* ---- the animations -------------------------------------------------- */

  var blinkAnim = null;

  function blink() {
    // Restart rather than queue, so a mashed button still looks like blinking.
    if (blinkAnim) { blinkAnim.cancel(); }
    // Four keyframes, not three: the lid holds shut between closedFrom and
    // closedTo. With a single instantaneous peak, a panel that is dropping
    // frames never paints the eyes actually closed, and the blink reads as the
    // lid stalling halfway down.
    blinkAnim = lid.animate([
      { transform: "translateY(" + LID_PARK + "px)", offset: 0, easing: "ease-in" },
      { transform: "translateY(0px)", offset: BLINK.closedFrom },
      { transform: "translateY(0px)", offset: BLINK.closedTo, easing: "ease-out" },
      { transform: "translateY(" + LID_PARK + "px)", offset: 1 }
    ], { duration: BLINK.ms });
    blinkAnim.onfinish = function () { blinkAnim = null; };
  }

  // Gaze latches; the CSS transition on .eye does the easing.
  //
  // The two eyes do not travel the same distance. Both irises rest close to
  // the notch between the eyes, so the one moving toward it runs out of white
  // almost immediately, while the one moving away has room to spare. Moving
  // them equally buries the inner iris and erases its shine. Giving the inner
  // eye a fraction of the travel keeps it readable and still reads as a glance.
  function gazeTo(direction) {
    for (var i = 0; i < eyes.length; i++) {
      var movingAwayFromNotch = (direction < 0) ? (i === 0) : (i === 1);
      var distance = direction * data.gazeTravel *
                     (movingAwayFromNotch ? 1 : data.gazeInnerRatio);
      eyes[i].style.transform = "translateX(" + distance + "px)";
    }
  }

  /* ---- the Chaos Emeralds ---------------------------------------------- */

  var EM = data.emeralds;
  var gemGroups = document.querySelectorAll(".gems");
  var emeraldAnims = [];
  var emeraldTimer = null;

  function easeOutCubic(u) { return 1 - Math.pow(1 - u, 3); }

  // Every gem flies the same trail at the same speed, one stagger apart: a
  // straight run in from off the side of the face, then a constant orbit
  // around the eye's centre. They all stop at the same instant, so the gem
  // that set off first has travelled furthest and ends up the furthest corner
  // round, while the last one barely clears the entry point. That ordering is
  // what makes it read as a snake rather than a fan opening out.
  function gemFrames(eye, slot) {
    var duration = EM.entryMs - slot * EM.staggerMs;
    var entry = eye.entry * Math.PI / 180;
    var startX = eye.cx + EM.entryRadius * Math.cos(entry);
    var startY = eye.cy + EM.entryRadius * Math.sin(entry);
    var ringX = eye.cx + EM.ringRadius * Math.cos(entry);
    var ringY = eye.cy + EM.ringRadius * Math.sin(entry);
    var frames = [];
    for (var k = 0; k <= 30; k++) {
      var t = duration * k / 30;          // this gem's own clock
      var x, y;
      if (t < EM.flyMs) {
        var u = t / EM.flyMs;             // linear, so the speed matches the
        x = startX + (ringX - startX) * u; // orbit it hands over to
        y = startY + (ringY - startY) * u;
      } else {
        var a = entry + (t - EM.flyMs) * EM.degPerMs * Math.PI / 180;
        x = eye.cx + EM.ringRadius * Math.cos(a);
        y = eye.cy + EM.ringRadius * Math.sin(a);
      }
      frames.push({
        offset: k / 30,
        transform: "translate(" + x + "px," + y + "px) scale(" + EM.gemScale + ")"
      });
    }
    return frames;
  }

  function stopEmeralds() {
    if (emeraldTimer) { clearTimeout(emeraldTimer); emeraldTimer = null; }
    for (var i = 0; i < emeraldAnims.length; i++) { emeraldAnims[i].cancel(); }
    emeraldAnims = [];
    var rings = document.querySelectorAll(".ring");
    for (var r = 0; r < rings.length; r++) { rings[r].classList.remove("spinning"); }
    stage.classList.remove("emeralds-on");
  }

  function showEmeralds() {
    if (!EM) { return; }              // server too old to describe them
    stopEmeralds();                   // a second press restarts the reveal
    stage.classList.add("emeralds-on");

    for (var e = 0; e < EM.eyes.length; e++) {
      var gems = gemGroups[e].querySelectorAll(".gem");
      for (var i = 0; i < gems.length; i++) {
        // fill "both" so a gem sits off-screen before its delay elapses and
        // holds its corner once it arrives.
        emeraldAnims.push(gems[i].animate(gemFrames(EM.eyes[e], i), {
          // Shorter duration for each later gem, same speed: that is how they
          // all arrive together having travelled different distances.
          duration: EM.entryMs - i * EM.staggerMs,
          delay: i * EM.staggerMs,
          easing: "linear",
          fill: "both"
        }));
      }
    }

    // The blue one waits for the octagon to close, then zooms in from behind.
    var settle = EM.entryMs;          // every gem lands at the same moment
    emeraldTimer = setTimeout(function () {
      for (var e = 0; e < EM.eyes.length; e++) {
        var eye = EM.eyes[e];
        var at = "translate(" + eye.cx + "px," + eye.cy + "px) ";
        emeraldAnims.push(gemGroups[e].querySelector(".gem-center").animate([
          { transform: at + "scale(0)", opacity: 0 },
          { transform: at + "scale(" + (EM.centerScale * 1.18) + ")",
            opacity: 1, offset: 0.7 },
          { transform: at + "scale(" + EM.centerScale + ")", opacity: 1 }
        ], { duration: EM.centerMs, easing: "ease-out", fill: "both" }));
        gemGroups[e].querySelector(".ring").classList.add("spinning");
      }
      emeraldTimer = null;
    }, settle);
  }

  /* ---- the "shoot Eggman" briefing -------------------------------------- */

  var SC = data.scene;
  var sceneAnims = [];
  var sceneTimer = null;
  var kidEl = document.querySelector(".actor.kid");
  var eggEl = document.querySelector(".actor.eggman");
  var dartEl = document.querySelector(".dart");
  var boomEl = document.querySelector(".boom");
  var poseAim = document.querySelector(".pose.aim");
  var poseCheer = document.querySelector(".pose.cheer");

  function place(x, y, s) {
    return "translate(" + x + "px," + y + "px) scale(" + s + ")";
  }

  function stopScene() {
    if (sceneTimer) { clearTimeout(sceneTimer); sceneTimer = null; }
    for (var i = 0; i < sceneAnims.length; i++) { sceneAnims[i].cancel(); }
    sceneAnims = [];
    stage.classList.remove("scene-on");
  }

  function showScene() {
    if (!SC) { return; }
    stopEmeralds();
    stopScene();                      // a second press restarts the briefing
    stage.classList.add("scene-on");

    var t = SC.t;
    var kx = SC.kid[0], ky = SC.kid[1];
    var ex = SC.eggman[0], ey = SC.eggman[1];
    var s = SC.scale;
    var mx = kx + SC.muzzle[0], my = ky + SC.muzzle[1];
    var ix = ex + SC.impact[0], iy = ey + SC.impact[1];

    function run(el, frames, options) {
      options.fill = "forwards";      // never "backwards": a delayed animation
      var a = el.animate(frames, options);   // must not paint before its beat
      sceneAnims.push(a);
      return a;
    }

    // Park them off the face before the first frame, so nothing flashes at the
    // origin between adding the class and the animation taking hold.
    kidEl.style.transform = place(kx - SC.entrance, ky, s);
    eggEl.style.transform = place(ex + SC.entrance, ey, s);

    var slide = { duration: SC.enterMs, easing: "cubic-bezier(.2,.75,.3,1)" };

    // 1. the kid runs in from the left, Eggman from the right
    run(kidEl, [{ transform: place(kx - SC.entrance, ky, s) },
                { transform: place(kx, ky, s) }], slide);
    run(eggEl, [{ transform: place(ex + SC.entrance, ey, s) },
                { transform: place(ex, ey, s) }], slide);

    // 2. the shot: a little recoil, and the dart crossing to Eggman
    run(kidEl, [{ transform: place(kx, ky, s) },
                { transform: place(kx - 3, ky, s), offset: 0.25 },
                { transform: place(kx, ky, s) }],
        { duration: SC.shotMs, delay: t.shot, easing: "ease-out" });
    // The dart lobs rather than flying straight: a straight shot crosses the
    // notch dividing the eyes, where the clip would hide it for half its
    // flight. The path is sampled in eyes/scene.py, which also tests that
    // every point of it lands on the white.
    var dartFrames = [];
    for (var d = 0; d < SC.dartPath.length; d++) {
      var pt = SC.dartPath[d];
      var next = SC.dartPath[Math.min(d + 1, SC.dartPath.length - 1)];
      var prev = SC.dartPath[Math.max(d - 1, 0)];
      var tilt = Math.atan2(next[1] - prev[1], next[0] - prev[0]) * 180 / Math.PI;
      dartFrames.push({
        offset: d / (SC.dartPath.length - 1),
        opacity: 1,
        transform: place(pt[0], pt[1], SC.dartScale) + " rotate(" + tilt + "deg)"
      });
    }
    dartFrames[dartFrames.length - 1].opacity = 0;   // gone as the blast starts
    run(dartEl, dartFrames,
        { duration: SC.shotMs, delay: t.shot, easing: "linear" });

    // 3. Eggman goes up, and the blast with him
    // Sized against the actors, not the raw artwork: the blast art is ~94
    // units tall and the whole eye is only 82, so scale 1 would overflow it.
    run(boomEl, [{ transform: place(ix, iy, s * 0.25), opacity: 0 },
                 { transform: place(ix, iy, s * 1.05), opacity: 1, offset: 0.25 },
                 { transform: place(ix, iy, s * 1.7), opacity: 0 }],
        { duration: SC.boomMs, delay: t.boom, easing: "ease-out" });
    run(eggEl, [{ transform: place(ex, ey, s * 1.15), opacity: 1 },
                { transform: place(ex, ey, s * 1.3), opacity: 1, offset: 0.35 },
                { transform: place(ex, ey, s * 0.1), opacity: 0 }],
        { duration: Math.round(SC.boomMs * 0.55), delay: t.boom, easing: "ease-in" });

    // 4. the kid cheers: swap pose and give a hop
    run(poseAim, [{ opacity: 1 }, { opacity: 0 }],
        { duration: 120, delay: t.cheer });
    run(poseCheer, [{ opacity: 0 }, { opacity: 1 }],
        { duration: 120, delay: t.cheer });
    run(kidEl, [{ transform: place(kx, ky, s) },
                { transform: place(kx, ky - 6, s), offset: 0.4 },
                { transform: place(kx, ky, s) }],
        { duration: 520, delay: t.cheer, easing: "ease-out" });

    // 5. everyone leaves and the eyes come back
    run(kidEl, [{ transform: place(kx, ky, s), opacity: 1 },
                { transform: place(kx - SC.entrance, ky, s), opacity: 1 }],
        { duration: SC.exitMs, delay: t.exit, easing: "ease-in" });

    sceneTimer = setTimeout(function () {
      stopScene();
      poseAim.style.opacity = "";     // ready for the next press
      poseCheer.style.opacity = "";
    }, t.end);
  }

  // Every other animation puts the eyes back, which is how the emeralds end.
  function andClearEmeralds(run) {
    return function () { stopEmeralds(); stopScene(); run(); };
  }

  var ANIMATIONS = {
    blink: andClearEmeralds(blink),
    look_left: andClearEmeralds(function () { gazeTo(-1); }),
    look_right: andClearEmeralds(function () { gazeTo(1); }),
    center: andClearEmeralds(function () { gazeTo(0); }),
    emeralds: function () { stopScene(); showEmeralds(); },
    shoot_eggman: showScene
  };

  function handle(message) {
    if (message.type === "anim") {
      var run = ANIMATIONS[message.name];
      if (run) { run(); }
    } else if (message.type === "calibration") {
      calibration = message.value;
      applyFit();
    }
  }

  /* ---- the link to the server ------------------------------------------ */

  function connect() {
    var scheme = location.protocol === "https:" ? "wss" : "ws";
    var ws = new WebSocket(scheme + "://" + location.host + "/ws");
    ws.onopen = function () { offline.hidden = true; };
    ws.onmessage = function (event) { handle(JSON.parse(event.data)); };
    ws.onerror = function () { ws.close(); };
    ws.onclose = function () {
      // The party outlasts any one Wi-Fi hiccup, so keep trying forever.
      offline.hidden = false;
      setTimeout(connect, 1000);
    };
  }

  /* ---- bench testing without a phone ----------------------------------- */

  document.addEventListener("keydown", function (event) {
    if (event.key === "b" || event.key === " ") { ANIMATIONS.blink(); }
    else if (event.key === "ArrowLeft") { ANIMATIONS.look_left(); }
    else if (event.key === "ArrowRight") { ANIMATIONS.look_right(); }
    else if (event.key === "ArrowDown") { ANIMATIONS.center(); }
    else if (event.key === "e") { ANIMATIONS.emeralds(); }
    else if (event.key === "s") { showScene(); }
    else { return; }
    event.preventDefault();
  });

  window.addEventListener("resize", applyFit);
  lid.style.transform = "translateY(" + LID_PARK + "px)";
  applyFit();
  connect();
})();
