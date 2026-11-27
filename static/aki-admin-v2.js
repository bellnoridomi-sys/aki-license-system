/* AKI CONTROL V2 — client-side admin enhancements; no server/API mutations */
(() => {
  "use strict";
  const path = window.location.pathname || "";
  if (!/^\/admin(?:\/|$)/.test(path) || path === "/admin/login") return;
  if (window.__AKI_ADMIN_V2__) return;
  window.__AKI_ADMIN_V2__ = true;

  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));
  const make = (tag, className, text) => {
    const el = document.createElement(tag);
    if (className) el.className = className;
    if (text !== undefined && text !== null) el.textContent = String(text);
    return el;
  };
  const clean = (value) => String(value || "").replace(/\s+/g, " ").trim();
  let toastNode;

  function toast(message) {
    if (!toastNode) {
      toastNode = make("div", "aki-v2-toast");
      toastNode.setAttribute("role", "status");
      toastNode.setAttribute("aria-live", "polite");
      document.body.appendChild(toastNode);
    }
    toastNode.textContent = message;
    toastNode.classList.add("aki-v2-toast-show");
    clearTimeout(toastNode._hideTimer);
    toastNode._hideTimer = setTimeout(() => toastNode.classList.remove("aki-v2-toast-show"), 2200);
  }

  function getLicenseTable() {
    return $$("table").find((table) => $("tbody tr", table)) || null;
  }

  function classify(text) {
    const value = clean(text).toLowerCase();
    if (/revok|thu h[oồ]i|đã x[oó]a|banned|disabled/.test(value)) return "revoked";
    if (/expired|hết hạn|quá hạn/.test(value)) return "expired";
    if (/unused|chưa kích hoạt|chưa dùng|pending|not activated/.test(value)) return "unused";
    if (/active|đang hoạt động|đã kích hoạt|valid|đang dùng/.test(value)) return "active";
    return "other";
  }

  function extractDate(text) {
    const match = clean(text).match(/\b(?:\d{4}[-/.]\d{1,2}[-/.]\d{1,2}|\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4})(?:[ T]\d{1,2}:\d{2}(?::\d{2})?)?\b/);
    return match ? match[0] : "";
  }

  function csvCell(value) {
    return '"' + String(value || "").replace(/"/g, '""').replace(/\r?\n/g, " ") + '"';
  }

  const table = getLicenseTable();
  let searchInput = null;
  let statusSelect = null;
  let countLabel = null;
  let emptyRow = null;
  const allRows = table ? $$("tbody tr", table).filter((row) => row.cells && row.cells.length) : [];
  let sortedRows = allRows.slice();
  let sortState = {index: -1, direction: 1};
  let drawer, drawerOverlay, paletteOverlay, paletteInput, paletteList;
  let currentDetailRow = null;

  function rowsForExport() {
    if (!table) return [];
    const headers = $$("thead th", table).map((th) => clean(th.innerText));
    const bodyRows = $$("tbody tr", table).filter((row) => row.style.display !== "none");
    const values = bodyRows.map((row) => Array.from(row.cells).map((cell) => clean(cell.innerText)));
    const includeActions = headers.some((header) => /action|thao tác/i.test(header));
    if (includeActions) {
      const actionIndex = headers.findIndex((header) => /action|thao tác/i.test(header));
      if (actionIndex >= 0) {
        headers.splice(actionIndex, 1);
        values.forEach((row) => row.splice(actionIndex, 1));
      }
    }
    return [headers.length ? headers : values[0].map((_, i) => "Cột " + (i + 1)), ...values];
  }

  function exportCsv() {
    const rows = rowsForExport();
    if (rows.length < 2) { toast("Không có license nào để xuất."); return; }
    const csv = "\uFEFF" + rows.map((row) => row.map(csvCell).join(",")).join("\r\n");
    const url = URL.createObjectURL(new Blob([csv], {type: "text/csv;charset=utf-8"}));
    const link = make("a");
    link.href = url;
    link.download = "aki-licenses-" + new Date().toISOString().slice(0, 10) + ".csv";
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
    toast("Đã xuất danh sách license đang hiển thị.");
  }

  function applyFilters() {
    if (!table) return;
    const query = clean(searchInput && searchInput.value).toLowerCase();
    const selected = statusSelect ? statusSelect.value : "all";
    let shown = 0;
    allRows.forEach((row) => {
      const content = clean(row.innerText).toLowerCase();
      const state = classify(content);
      const match = (!query || content.includes(query)) && (selected === "all" || state === selected);
      row.style.display = match ? "" : "none";
      if (match) shown += 1;
    });
    if (countLabel) countLabel.textContent = shown + " / " + allRows.length + " LICENSE";
    if (emptyRow) emptyRow.remove();
    if (shown === 0) {
      emptyRow = document.createElement("tr");
      const cell = make("td", "aki-v2-empty", "Không tìm thấy license phù hợp.");
      cell.colSpan = Math.max(1, table.querySelectorAll("thead th").length || (allRows[0] ? allRows[0].cells.length : 1));
      emptyRow.appendChild(cell);
      $("tbody", table).appendChild(emptyRow);
    }
  }

  function sortBy(index, header) {
    if (!table || index < 0) return;
    sortState.direction = sortState.index === index ? sortState.direction * -1 : 1;
    sortState.index = index;
    const body = $("tbody", table);
    const visible = allRows.slice().sort((a, b) => {
      const left = clean(a.cells[index] && a.cells[index].innerText);
      const right = clean(b.cells[index] && b.cells[index].innerText);
      const leftNumber = Number(left.replace(/[^\d.-]/g, ""));
      const rightNumber = Number(right.replace(/[^\d.-]/g, ""));
      const numeric = left && right && Number.isFinite(leftNumber) && Number.isFinite(rightNumber) &&
        /[\d]/.test(left) && /[\d]/.test(right);
      const result = numeric ? leftNumber - rightNumber : left.localeCompare(right, "vi", {numeric: true, sensitivity: "base"});
      return result * sortState.direction;
    });
    visible.forEach((row) => body.appendChild(row));
    allRows.splice(0, allRows.length, ...visible);
    $$("thead th", table).forEach((th) => th.removeAttribute("aria-sort"));
    header.setAttribute("aria-sort", sortState.direction === 1 ? "ascending" : "descending");
    applyFilters();
  }

  function createDrawer() {
    drawerOverlay = make("div", "aki-v2-overlay");
    drawerOverlay.style.display = "none";
    drawerOverlay.addEventListener("click", closeDrawer);
    drawer = make("aside", "aki-v2-drawer");
    drawer.setAttribute("role", "dialog");
    drawer.setAttribute("aria-modal", "true");
    drawer.setAttribute("aria-label", "Chi tiết license");
    const head = make("div", "aki-v2-drawer-head");
    const headingWrap = make("div");
    headingWrap.appendChild(make("p", "aki-v2-drawer-kicker", "AKI / LICENSE DETAIL"));
    const title = make("h2", "aki-v2-drawer-title", "License details");
    title.id = "aki-v2-drawer-title";
    headingWrap.appendChild(title);
    const close = make("button", "aki-v2-btn aki-v2-drawer-close", "×");
    close.type = "button";
    close.setAttribute("aria-label", "Đóng chi tiết");
    close.addEventListener("click", closeDrawer);
    head.append(headingWrap, close);
    const body = make("div", "aki-v2-drawer-body");
    body.appendChild(make("dl", "aki-v2-detail-list"));
    const foot = make("div", "aki-v2-drawer-foot");
    const copy = make("button", "aki-v2-btn aki-v2-btn-primary", "Sao chép thông tin");
    copy.type = "button";
    copy.addEventListener("click", () => {
      if (!currentDetailRow) return;
      const text = Array.from(currentDetailRow.cells).map((cell, i) => {
        const headers = $$("thead th", table).map((th) => clean(th.innerText));
        return (headers[i] || ("Cột " + (i + 1))) + ": " + clean(cell.innerText);
      }).join("\n");
      navigator.clipboard.writeText(text).then(() => toast("Đã sao chép thông tin license."))
        .catch(() => toast("Trình duyệt chưa cho phép sao chép."));
    });
    const openTable = make("button", "aki-v2-btn", "Về bảng license");
    openTable.type = "button";
    openTable.addEventListener("click", closeDrawer);
    foot.append(copy, openTable);
    drawer.append(head, body, foot);
    document.body.append(drawerOverlay, drawer);
  }

  function openDrawer(row) {
    if (!drawer) createDrawer();
    if (!row || !table) return;
    currentDetailRow = row;
    const cells = Array.from(row.cells);
    const headers = $$("thead th", table).map((th) => clean(th.innerText));
    const list = $(".aki-v2-detail-list", drawer);
    list.replaceChildren();
    let firstValue = "";
    cells.forEach((cell, index) => {
      const label = headers[index] || ("Thông tin " + (index + 1));
      if (/action|thao tác/i.test(label)) return;
      const value = clean(cell.innerText);
      if (!firstValue && value) firstValue = value;
      const item = make("div", "aki-v2-detail-row");
      item.append(make("dt", "", label), make("dd", "", value || "—"));
      list.appendChild(item);
    });
    $(".aki-v2-drawer-title", drawer).textContent = firstValue ? firstValue.slice(0, 74) : "License details";
    drawerOverlay.style.display = "flex";
    requestAnimationFrame(() => drawer.classList.add("aki-v2-open"));
    document.body.style.overflow = "hidden";
    const closeButton = $(".aki-v2-drawer-close", drawer);
    if (closeButton) closeButton.focus();
  }

  function closeDrawer() {
    if (!drawer) return;
    drawer.classList.remove("aki-v2-open");
    if (drawerOverlay) drawerOverlay.style.display = "none";
    document.body.style.overflow = "";
    currentDetailRow = null;
  }

  function buildTableTools() {
    if (!table || !allRows.length || $(".aki-v2-toolbar")) return;
    const toolbar = make("section", "aki-v2-toolbar");
    toolbar.setAttribute("aria-label", "Công cụ lọc license");
    const searchWrap = make("label", "aki-v2-search-wrap");
    const icon = make("span", "aki-v2-search-icon", "⌕");
    icon.setAttribute("aria-hidden", "true");
    searchInput = make("input", "aki-v2-search");
    searchInput.type = "search";
    searchInput.placeholder = "Tìm key, người dùng, trạng thái…";
    searchInput.setAttribute("aria-label", "Tìm trong danh sách license");
    searchInput.addEventListener("input", applyFilters);
    searchWrap.append(icon, searchInput);
    statusSelect = make("select", "aki-v2-status-select");
    statusSelect.setAttribute("aria-label", "Lọc theo trạng thái");
    [
      ["all", "Tất cả trạng thái"],
      ["active", "Đang hoạt động"],
      ["unused", "Chưa kích hoạt"],
      ["expired", "Hết hạn"],
      ["revoked", "Đã thu hồi"],
      ["other", "Khác / chưa phân loại"]
    ].forEach(([value, label]) => {
      const option = make("option", "", label);
      option.value = value;
      statusSelect.appendChild(option);
    });
    statusSelect.addEventListener("change", applyFilters);
    const actions = make("div", "aki-v2-toolbar-actions");
    const reset = make("button", "aki-v2-btn", "Đặt lại");
    reset.type = "button";
    reset.addEventListener("click", () => {
      searchInput.value = "";
      statusSelect.value = "all";
      applyFilters();
    });
    const exportButton = make("button", "aki-v2-btn aki-v2-btn-primary", "↓ Xuất CSV");
    exportButton.type = "button";
    exportButton.addEventListener("click", exportCsv);
    actions.append(reset, exportButton);
    toolbar.append(searchWrap, statusSelect, actions);
    table.parentElement.insertBefore(toolbar, table);

    const count = make("div", "aki-v2-countline");
    count.append(make("span", "", "LICENSE WORKSPACE"), make("strong", "", allRows.length + " / " + allRows.length + " LICENSE"));
    toolbar.insertAdjacentElement("afterend", count);
    countLabel = count.querySelector("strong");

    const wrapper = table.closest(".table-wrap,.table-container") || table.parentElement;
    if (wrapper) wrapper.classList.add("aki-v2-table-wrap");
    $$("thead th", table).forEach((th, index) => {
      th.tabIndex = 0;
      th.setAttribute("role", "button");
      th.setAttribute("aria-label", clean(th.innerText) + " — sắp xếp");
      th.addEventListener("click", () => sortBy(index, th));
      th.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") { event.preventDefault(); sortBy(index, th); }
      });
    });
    allRows.forEach((row) => {
      row.classList.add("aki-v2-row");
      row.tabIndex = 0;
      row.setAttribute("aria-label", "Mở chi tiết license");
      row.addEventListener("click", (event) => {
        if (event.target.closest("a,button,input,select,textarea,form,label")) return;
        openDrawer(row);
      });
      row.addEventListener("keydown", (event) => {
        if ((event.key === "Enter" || event.key === " ") && event.target === row) {
          event.preventDefault();
          openDrawer(row);
        }
      });
    });
    applyFilters();
    buildTimeline();
  }

  function buildTimeline() {
    if (!table || !allRows.length || $(".aki-v2-timeline")) return;
    const section = make("section", "aki-v2-timeline");
    const heading = make("div", "aki-v2-section-head");
    const titleWrap = make("div");
    titleWrap.append(make("h2", "aki-v2-section-title", "License activity"));
    titleWrap.append(make("p", "aki-v2-section-sub", "Tổng hợp từ các license đang có trong bảng — không phải nhật ký thao tác."));
    heading.append(titleWrap, make("span", "aki-v2-admin-mark", "AKI CONTROL"));
    const list = make("div", "aki-v2-timeline-list");
    allRows.slice(0, 5).forEach((row) => {
      const cells = Array.from(row.cells);
      const headers = $$("thead th", table).map((th) => clean(th.innerText));
      const keyCellIndex = headers.findIndex((header) => /key|license|mã/i.test(header));
      const title = clean(cells[keyCellIndex >= 0 ? keyCellIndex : 0] && cells[keyCellIndex >= 0 ? keyCellIndex : 0].innerText) || "License record";
      const status = classify(row.innerText);
      const statusLabels = {active:"Đang hoạt động",unused:"Chưa kích hoạt",expired:"Đã hết hạn",revoked:"Đã thu hồi",other:"Chưa phân loại"};
      const date = extractDate(row.innerText);
      const event = make("div", "aki-v2-event");
      event.appendChild(make("span", "aki-v2-event-dot"));
      const copy = make("div");
      copy.append(make("div", "aki-v2-event-title", title.length > 44 ? title.slice(0, 41) + "…" : title));
      copy.append(make("div", "aki-v2-event-meta", "Trạng thái: " + statusLabels[status]));
      const dateNode = make("time", "aki-v2-event-date", date || "Trong danh sách");
      if (date) dateNode.dateTime = date;
      event.append(copy, dateNode);
      event.tabIndex = 0;
      event.setAttribute("role", "button");
      event.setAttribute("aria-label", "Xem chi tiết " + title);
      event.addEventListener("click", () => openDrawer(row));
      event.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); openDrawer(row); } });
      list.appendChild(event);
    });
    section.append(heading, list);
    const host = table.closest(".table-wrap,.table-container") || table.parentElement;
    if (host) host.insertAdjacentElement("afterend", section);
  }

  function buildPalette() {
    if (paletteOverlay) return;
    paletteOverlay = make("div", "aki-v2-overlay");
    paletteOverlay.style.display = "none";
    paletteOverlay.addEventListener("click", (event) => { if (event.target === paletteOverlay) closePalette(); });
    const panel = make("section", "aki-v2-command");
    panel.setAttribute("role", "dialog");
    panel.setAttribute("aria-modal", "true");
    panel.setAttribute("aria-label", "AKI command palette");
    const top = make("div", "aki-v2-command-top");
    top.appendChild(make("span", "aki-v2-command-mark", "⌘"));
    paletteInput = make("input", "aki-v2-command-search");
    paletteInput.type = "search";
    paletteInput.placeholder = "Bạn muốn thực hiện thao tác nào?";
    paletteInput.setAttribute("aria-label", "Tìm lệnh");
    paletteInput.addEventListener("input", renderCommands);
    top.appendChild(paletteInput);
    panel.appendChild(top);
    paletteList = make("div", "aki-v2-command-list");
    panel.appendChild(paletteList);
    const foot = make("div", "aki-v2-command-foot");
    foot.append(make("span", "", "↑ ↓ điều hướng · Enter chọn"), make("span", "", "ESC đóng"));
    panel.appendChild(foot);
    paletteOverlay.appendChild(panel);
    document.body.appendChild(paletteOverlay);
    paletteInput.addEventListener("keydown", (event) => {
      const buttons = $$(".aki-v2-command-item", paletteList);
      const active = buttons.indexOf(document.activeElement);
      if (event.key === "ArrowDown" && buttons.length) { event.preventDefault(); buttons[Math.min(active + 1, buttons.length - 1)].focus(); }
      if (event.key === "ArrowUp" && buttons.length) { event.preventDefault(); buttons[Math.max(active - 1, 0)].focus(); }
    });
    renderCommands();
  }

  function commandItems() {
    const hasTable = Boolean(table);
    const createLink = $("a[href*='/admin/keys/create']");
    const items = [
      {group:"Điều hướng",icon:"⌂",title:"Mở Dashboard",desc:"Quay về tổng quan license",key:"G D",run:() => { window.location.href = "/admin"; }},
      {group:"Điều hướng",icon:"+",title:"Tạo license mới",desc:"Mở biểu mẫu tạo key",key:"G N",run:() => { window.location.href = createLink ? createLink.href : "/admin/keys/create"; }},
      {group:"Bảng license",icon:"⌕",title:"Tìm license",desc:"Đặt con trỏ vào ô tìm kiếm",key:"/",run:() => { if (searchInput) searchInput.focus(); else toast("Trang này chưa có bảng license."); }},
      {group:"Bảng license",icon:"↺",title:"Xóa bộ lọc",desc:"Hiển thị lại tất cả license",key:"R",run:() => { if (searchInput) searchInput.value = ""; if (statusSelect) statusSelect.value = "all"; applyFilters(); toast("Đã đặt lại bộ lọc."); }},
      {group:"Bảng license",icon:"↓",title:"Xuất CSV",desc:"Tải xuống các dòng đang hiển thị",key:"E",run:exportCsv},
      {group:"Hệ thống",icon:"⟳",title:"Làm mới trang",desc:"Tải lại dữ liệu mới nhất từ máy chủ",key:"Ctrl R",run:() => window.location.reload()}
    ];
    return hasTable ? items : items.filter((item) => item.title !== "Tìm license" && item.title !== "Xóa bộ lọc" && item.title !== "Xuất CSV");
  }

  function renderCommands() {
    if (!paletteList) return;
    const query = clean(paletteInput && paletteInput.value).toLowerCase();
    paletteList.replaceChildren();
    let currentGroup = "";
    let count = 0;
    commandItems().forEach((item) => {
      if (query && !(item.title + " " + item.desc + " " + item.group).toLowerCase().includes(query)) return;
      if (currentGroup !== item.group) {
        currentGroup = item.group;
        paletteList.appendChild(make("div", "aki-v2-command-group", currentGroup));
      }
      const button = make("button", "aki-v2-command-item");
      button.type = "button";
      button.appendChild(make("span", "aki-v2-command-icon", item.icon));
      const copy = make("span", "aki-v2-command-copy");
      copy.append(make("span", "aki-v2-command-name", item.title), make("span", "aki-v2-command-desc", item.desc));
      button.append(copy, make("kbd", "aki-v2-command-key", item.key));
      button.addEventListener("click", () => { closePalette(); item.run(); });
      paletteList.appendChild(button);
      count += 1;
    });
    if (!count) paletteList.appendChild(make("div", "aki-v2-command-empty", "Không có lệnh phù hợp."));
  }

  function openPalette() {
    buildPalette();
    paletteOverlay.style.display = "flex";
    document.body.style.overflow = "hidden";
    paletteInput.value = "";
    renderCommands();
    requestAnimationFrame(() => paletteInput.focus());
  }

  function closePalette() {
    if (!paletteOverlay) return;
    paletteOverlay.style.display = "none";
    document.body.style.overflow = "";
  }

  function addShortcut() {
    const button = make("button", "aki-v2-shortcut");
    button.type = "button";
    button.setAttribute("aria-label", "Mở bảng lệnh nhanh, Ctrl hoặc Command cộng K");
    button.append(make("span", "", "AKI COMMAND"), make("kbd", "", "CTRL K"));
    button.addEventListener("click", openPalette);
    document.body.appendChild(button);
  }

  function markNavigation() {
    $$("a[href]").forEach((link) => {
      try {
        const url = new URL(link.href, window.location.origin);
        if (url.origin !== window.location.origin) return;
        if (url.pathname === path || (path === "/admin" && url.pathname === "/admin/")) link.classList.add("aki-v2-current-nav");
      } catch (_) {}
    });
    const headings = $$("h1");
    if (headings.length && !$(".aki-v2-admin-mark", headings[0].parentElement || document)) {
      headings[0].insertAdjacentElement("afterend", make("span", "aki-v2-admin-mark", "CONTROL V2"));
    }
  }

  document.addEventListener("keydown", (event) => {
    const key = event.key.toLowerCase();
    if ((event.ctrlKey || event.metaKey) && key === "k") { event.preventDefault(); openPalette(); return; }
    if (event.key === "Escape") { closePalette(); closeDrawer(); }
    if (!paletteOverlay || paletteOverlay.style.display === "none") return;
    if (event.key === "Enter" && document.activeElement === paletteInput) {
      const first = $(".aki-v2-command-item", paletteList);
      if (first) first.click();
    }
  });

  buildTableTools();
  addShortcut();
  markNavigation();
  if (!reduced) {
    const targets = $$(".aki-v2-toolbar,.aki-v2-timeline");
    targets.forEach((el, index) => {
      el.style.opacity = "0";
      el.style.transform = "translateY(10px)";
      el.style.transition = "opacity .55s ease " + (index * 80) + "ms,transform .55s cubic-bezier(.2,.78,.2,1) " + (index * 80) + "ms";
      requestAnimationFrame(() => { el.style.opacity = "1"; el.style.transform = "translateY(0)"; });
    });
  }
})();
