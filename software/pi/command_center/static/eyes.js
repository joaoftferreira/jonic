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

  // Every other animation puts the eyes back, which is how the emeralds end.
  function andClearEmeralds(run) {
    return function () { stopEmeralds(); run(); };
  }

  var ANIMATIONS = {
    blink: andClearEmeralds(blink),
    look_left: andClearEmeralds(function () { gazeTo(-1); }),
    look_right: andClearEmeralds(function () { gazeTo(1); }),
    center: andClearEmeralds(function () { gazeTo(0); }),
    emeralds: showEmeralds
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
    else if (event.key === "e") { showEmeralds(); }
    else { return; }
    event.preventDefault();
  });

  window.addEventListener("resize", applyFit);
  lid.style.transform = "translateY(" + LID_PARK + "px)";
  applyFit();
  connect();
})();
