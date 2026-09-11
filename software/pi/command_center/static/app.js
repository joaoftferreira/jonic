/* The phone remote. Buttons POST to /fire/<id>; sliders POST calibration.
   Nothing here animates: the LCD page owns that. */
(function () {
  "use strict";

  /* ---- action buttons --------------------------------------------------- */

  document.querySelectorAll("button.action").forEach(function (el) {
    el.addEventListener("click", function () {
      el.classList.add("fired");
      setTimeout(function () { el.classList.remove("fired"); }, 400);
      fetch("/fire/" + el.dataset.id, { method: "POST" }).catch(function () {});
    });
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
})();
