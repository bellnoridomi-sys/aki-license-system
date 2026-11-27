// Lucian UX/UI Prompt #426 · MIT License (c) 2026 Seokwoooo · https://lucianlabs.dev/uxui-prompt/#426
// From Uiverse.io by dylanharriscameron - https://uiverse.io/dylanharriscameron/stupid-mole-90
// MIT License, Copyright (c) dylanharriscameron (Dylan)
(() => {
  const roots = document.querySelectorAll(".u426");
  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const digits = "01234567890123456789".split("");

  function buildStats(root) {
    const cells = [...root.querySelectorAll(".u426-c")];
    const columns = cells.map((cell) => {
      const value = cell.dataset.v || "0";
      const number = cell.querySelector(".u426-n");
      const label = cell.querySelector("small")?.textContent?.trim() || "Statistic";
      const rolls = [];
      let index = 0;
      number.replaceChildren();
      cell.tabIndex = 0;
      cell.setAttribute("aria-label", label + ": " + value);
      number.setAttribute("aria-hidden", "true");

      for (const character of value) {
        if (/\d/.test(character)) {
          const column = document.createElement("span");
          column.className = "u426-col";
          const reel = document.createElement("span");
          reel.style.setProperty("--k", String(index++));
          reel.dataset.d = character;
          for (const digit of digits) {
            const item = document.createElement("b");
            item.textContent = digit;
            reel.appendChild(item);
          }
          column.appendChild(reel);
          number.appendChild(column);
          rolls.push(reel);
        } else {
          const separator = document.createElement("i");
          separator.textContent = character;
          number.appendChild(separator);
        }
      }
      return {cell, rolls, lastRoll: 0};
    });

    function roll(columns, fromStart) {
      columns.forEach((reel) => {
        const target = Number(reel.dataset.d);
        reel.style.transition = "none";
        reel.style.setProperty("--d", fromStart === null ? target : fromStart);
      });
      void root.offsetWidth;
      columns.forEach((reel) => {
        reel.style.transition = "";
        reel.style.setProperty("--d", Number(reel.dataset.d) + 10);
      });
    }

    let shown = false;
    function reveal() {
      if (shown) return;
      shown = true;
      columns.forEach(({rolls}) => {
        if (reduced) rolls.forEach((reel) => reel.style.setProperty("--d", Number(reel.dataset.d) + 10));
        else roll(rolls, 0);
      });
    }

    columns.forEach((item) => {
      const reroll = () => {
        if (!shown || reduced || Date.now() - item.lastRoll < 900) return;
        item.lastRoll = Date.now();
        roll(item.rolls, null);
      };
      item.cell.addEventListener("pointerenter", reroll);
      item.cell.addEventListener("focus", reroll);
    });

    if ("IntersectionObserver" in window) {
      const observer = new IntersectionObserver((entries) => {
        if (entries[0]?.isIntersecting) {
          reveal();
          observer.disconnect();
        }
      }, {threshold: 0.5});
      observer.observe(root);
    } else reveal();
  }

  roots.forEach(buildStats);

  document.querySelectorAll(".aki-uv-discord").forEach((button) => {
    button.addEventListener("click", async () => {
      const username = button.dataset.discord || "s0l";
      const status = button.closest(".aki-uv-bg")?.querySelector(".aki-uv-status");
      try {
        await navigator.clipboard.writeText(username);
        if (status) status.textContent = "Đã sao chép Discord: " + username;
        button.textContent = "ĐÃ SAO CHÉP ✓";
      } catch {
        if (status) status.textContent = "Discord của AKI Dev: " + username;
      }
    });
  });
})();
