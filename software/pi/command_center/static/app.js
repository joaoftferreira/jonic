/* The phone remote. Buttons POST to /fire/<id>; sliders POST calibration.
   Nothing here animates: the LCD page owns that. */
(function () {
  "use strict";

  /* ---- action buttons --------------------------------------------------- */

  function fire(id) {
    return fetch("/fire/" + id, { method: "POST" }).catch(function () {});
  }

  document.querySelectorAll("button.action").forEach(function (el) {
    if (el.dataset.hold) { return; }   // held buttons are driven below
    el.addEventListener("click", function () {
      el.classList.add("fired");
      setTimeout(function () { el.classList.remove("fired"); }, 400);
      fire(el.dataset.id);
    });
  });

  /* ---- hold to drive ---------------------------------------------------- */

  // Holding a direction repeats the command; the robot stops itself if the
  // repeats stop arriving, so the worst case is that it coasts to a halt.
  var DRIVE_REPEAT = parseInt(document.body.dataset.driveRepeat, 10) || 200;
  var holdTimer = null;
  var holdButton = null;

  function startHold(el) {
    if (holdTimer) { return; }
    holdButton = el;
    el.classList.add("holding");
    fire(el.dataset.id);
    holdTimer = setInterval(function () { fire(el.dataset.id); }, DRIVE_REPEAT);
  }

  function endHold() {
    if (!holdTimer) { return; }
    clearInterval(holdTimer);
    holdTimer = null;
    if (holdButton) { holdButton.classList.remove("holding"); holdButton = null; }
    fire("robot_stop");     // immediate; the firmware timeout is the backstop
  }

  document.querySelectorAll("button.action[data-hold]").forEach(function (el) {
    el.addEventListener("pointerdown", function (event) {
      event.preventDefault();          // no text selection or page scroll
      startHold(el);
    });
  });

  // Release anywhere stops, including a finger that slid off the button. The
  // window-level events cover the cases that actually strand a robot: the
  // phone locking, the browser going to the background, a call coming in.
  ["pointerup", "pointercancel"].forEach(function (name) {
    window.addEventListener(name, endHold);
  });
  window.addEventListener("blur", endHold);
  document.addEventListener("visibilitychange", function () {
    if (document.hidden) { endHold(); }
  });

  /* ---- status ----------------------------------------------------------- */

  var status = document.getElementById("status");

  function pill(label, up) {
    return '<span class="pill ' + (up ? "up" : "down") + '">' +
           label + " " + (up ? "●" : "○") + "</span>";
  }

  function poll() {
    fetch("/status").then(function (r) { return r.json(); }).then(function (s) {
      var html = pill("eyes", s.eyes > 0);
      Object.keys(s.nodes).forEach(function (n) {
        html += pill(n, s.nodes[n]);
      });
      status.innerHTML = html;
    }).catch(function () {});
  }
  setInterval(poll, 3000);
  poll();

  /* ---- calibration ------------------------------------------------------ */

  var sliders = Array.prototype.slice.call(
    document.querySelectorAll("#calibration input[type=range]"));

  function readSliders() {
    var value = {};
    sliders.forEach(function (s) { value[s.name] = parseFloat(s.value); });
    return value;
  }

  function showValues() {
    sliders.forEach(function (s) {
      var out = s.parentNode.querySelector("output");
      // Scales read as a multiplier, offsets as whole pixels.
      out.textContent = s.step < 1 ? parseFloat(s.value).toFixed(2)
                                   : Math.round(s.value) + "px";
    });
  }

  // A drag fires dozens of input events a second. Coalesce them onto one
  // in-flight request so the Pi is not answering a queue of stale positions.
  var inFlight = false;
  var pending = null;

  function push(value, persist) {
    if (inFlight && !persist) { pending = value; return; }
    inFlight = true;
    fetch("/eyes/calibration", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ value: value, persist: !!persist })
    }).catch(function () {}).then(function () {
      inFlight = false;
      if (pending) {
        var next = pending;
        pending = null;
        push(next, false);
      }
    });
  }

  sliders.forEach(function (s) {
    s.addEventListener("input", function () {
      showValues();
      push(readSliders(), false);
    });
  });

  var save = document.getElementById("cal-save");
  if (save) {
    save.addEventListener("click", function () {
      push(readSliders(), true);
      save.textContent = "Saved ✓";
      setTimeout(function () { save.textContent = "Save"; }, 1200);
    });
  }

  var reset = document.getElementById("cal-reset");
  if (reset) {
    reset.addEventListener("click", function () {
      sliders.forEach(function (s) {
        s.value = s.name.indexOf("scale") === 0 ? 1 : 0;
      });
      showValues();
      push(readSliders(), false);
    });
  }

  showValues();

  /* ---- motor speed ------------------------------------------------------ */

  var speed = document.getElementById("robot-speed");
  if (speed) {
    var speedOut = speed.parentNode.querySelector("output");
    var speedInFlight = false;
    var speedPending = null;

    function pushSpeed(value, persist) {
      if (speedInFlight && !persist) { speedPending = value; return; }
      speedInFlight = true;
      fetch("/robot/speed", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ value: { speed: value }, persist: !!persist })
      }).catch(function () {}).then(function () {
        speedInFlight = false;
        if (speedPending !== null) {
          var next = speedPending;
          speedPending = null;
          pushSpeed(next, false);
        }
      });
    }

    speed.addEventListener("input", function () {
      speedOut.textContent = Math.round(speed.value) + "%";
      pushSpeed(parseFloat(speed.value), false);
    });
    speedOut.textContent = Math.round(speed.value) + "%";

    var speedSave = document.getElementById("speed-save");
    if (speedSave) {
      speedSave.addEventListener("click", function () {
        pushSpeed(parseFloat(speed.value), true);
        speedSave.textContent = "Saved ✓";
        setTimeout(function () { speedSave.textContent = "Save speed"; }, 1200);
      });
    }
  }
})();
