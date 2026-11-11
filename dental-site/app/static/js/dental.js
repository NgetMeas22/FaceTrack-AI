/**
 * Dental Clinic Official Website — Minimal Deferred Vanilla JS
 * Handles mobile menu drawer, accessible FAQ accordions, and safe form submit locking.
 */
(function () {
  "use strict";

  document.addEventListener("DOMContentLoaded", function () {
    initMobileDrawer();
    initFaqAccordions();
    initBookingFormUX();
  });

  function initMobileDrawer() {
    var toggle = document.getElementById("mobile-menu-toggle");
    var drawer = document.getElementById("mobile-nav-drawer");
    if (!toggle || !drawer) return;

    toggle.addEventListener("click", function () {
      var isOpen = toggle.getAttribute("aria-expanded") === "true";
      toggle.setAttribute("aria-expanded", String(!isOpen));
      drawer.hidden = isOpen;
      if (!isOpen) {
        var firstLink = drawer.querySelector("a");
        if (firstLink) firstLink.focus();
      }
    });

    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape" && toggle.getAttribute("aria-expanded") === "true") {
        toggle.setAttribute("aria-expanded", "false");
        drawer.hidden = true;
        toggle.focus();
      }
    });
  }

  function initFaqAccordions() {
    var triggers = document.querySelectorAll("[data-accordion-trigger]");
    triggers.forEach(function (btn) {
      btn.addEventListener("click", function () {
        var targetId = btn.getAttribute("aria-controls");
        var panel = targetId ? document.getElementById(targetId) : null;
        if (!panel) return;
        var expanded = btn.getAttribute("aria-expanded") === "true";
        btn.setAttribute("aria-expanded", String(!expanded));
        panel.hidden = expanded;
      });
    });
  }

  function initBookingFormUX() {
    var forms = document.querySelectorAll("form[data-lock-submit]");
    forms.forEach(function (form) {
      form.addEventListener("submit", function () {
        var submitBtn = form.querySelector('button[type="submit"]');
        if (submitBtn && !submitBtn.disabled) {
          submitBtn.disabled = true;
          var sendingText = submitBtn.getAttribute("data-sending-text");
          if (sendingText) {
            submitBtn.textContent = sendingText;
          }
        }
      });
    });

    // Enforce Sunday closed warning client-side as gentle enhancement (server always re-validates)
    var dateInput = document.getElementById("preferred_date");
    var dateHint = document.getElementById("date-closed-hint");
    if (dateInput && dateHint) {
      dateInput.addEventListener("change", function () {
        if (!dateInput.value) {
          dateHint.hidden = true;
          return;
        }
        var parts = dateInput.value.split("-");
        if (parts.length === 3) {
          var chosen = new Date(Number(parts[0]), Number(parts[1]) - 1, Number(parts[2]));
          var isSunday = chosen.getDay() === 0;
          dateHint.hidden = !isSunday;
        }
      });
    }
  }
})();
