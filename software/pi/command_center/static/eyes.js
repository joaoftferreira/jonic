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

  var ANIMATIONS = {
    blink: blink,
    look_left: function () { gazeTo(-1); },
    look_right: function () { gazeTo(1); },
    center: function () { gazeTo(0); }
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
    if (event.key === "b" || event.key === " ") { blink(); }
    else if (event.key === "ArrowLeft") { gazeTo(-1); }
    else if (event.key === "ArrowRight") { gazeTo(1); }
    else if (event.key === "ArrowDown") { gazeTo(0); }
    else { return; }
    event.preventDefault();
  });

  window.addEventListener("resize", applyFit);
  lid.style.transform = "translateY(" + LID_PARK + "px)";
  applyFit();
  connect();
})();
