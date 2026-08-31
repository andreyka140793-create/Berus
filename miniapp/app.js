const tg = window.Telegram?.WebApp;
if (tg) {
  tg.ready();
  tg.expand();
  document.documentElement.style.setProperty("--bg", tg.themeParams.bg_color || "#0b1220");
}

const state = {
  meta: { cities: [], categories: [] },
  me: null,
  currentOrderId: null,
};

function initData() {
  if (tg?.initData) return tg.initData;
  // локальная отладка в браузере
  return "dev:10001";
}

async function api(path, options = {}) {
  const headers = Object.assign(
    { "Content-Type": "application/json", "X-Telegram-Init-Data": initData() },
    options.headers || {}
  );
  const res = await fetch(path, { ...options, headers });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || data.message || res.statusText);
  return data;
}

function fillSelect(el, items, withAll) {
  el.innerHTML = "";
  if (withAll) {
    const o = document.createElement("option");
    o.value = "";
    o.textContent = "Все";
    el.appendChild(o);
  }
  items.forEach((it) => {
    const o = document.createElement("option");
    o.value = it.slug;
    o.textContent = it.name;
    el.appendChild(o);
  });
}

function cityName(slug) {
  return state.meta.cities.find((c) => c.slug === slug)?.name || slug;
}
function catName(slug) {
  return state.meta.categories.find((c) => c.slug === slug)?.name || slug;
}

function showTab(name) {
  document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
  document.querySelectorAll(".tabs button").forEach((b) => b.classList.remove("active"));
  const tab = document.getElementById("tab-" + name);
  if (tab) tab.classList.add("active");
  const btn = document.querySelector(`.tabs button[data-tab="${name}"]`);
  if (btn) btn.classList.add("active");
}

async function loadFeed() {
  const city = document.getElementById("filter-city").value;
  const cat = document.getElementById("filter-cat").value;
  const q = new URLSearchParams({ status: "open" });
  if (city) q.set("city_slug", city);
  if (cat) q.set("category_slug", cat);
  const rows = await api("/api/orders?" + q.toString());
  const box = document.getElementById("orders-list");
  if (!rows.length) {
    box.innerHTML = '<div class="card"><p>Пока нет открытых заявок. Создайте первую!</p></div>';
    return;
  }
  box.innerHTML = rows
    .map(
      (o) => `
    <div class="card" data-id="${o.id}">
      <h4>${escapeHtml(o.title)}</h4>
      <p>${escapeHtml(o.description).slice(0, 140)}</p>
      <div class="meta">${cityName(o.city_slug)} · ${catName(o.category_slug)} · откликов: ${o.bids_count}${
        o.budget ? " · до " + o.budget + " ₽" : ""
      }</div>
    </div>`
    )
    .join("");
  box.querySelectorAll(".card[data-id]").forEach((el) => {
    el.onclick = () => openOrder(el.getAttribute("data-id"));
  });
}

async function openOrder(id) {
  state.currentOrderId = id;
  const o = await api("/api/orders/" + id);
  const box = document.getElementById("order-detail");
  const bids = (o.bids || [])
    .map(
      (b) =>
        `<div class="card"><p><b>${escapeHtml(b.performer.full_name || b.performer.username || "Исполнитель")}</b> · ★ ${
          b.performer.rating
        }</p><p>${escapeHtml(b.message)}</p>${
          b.price ? `<div class="meta">${b.price} ₽</div>` : ""
        }</div>`
    )
    .join("");
  box.innerHTML = `
    <div class="card">
      <h4>${escapeHtml(o.title)}</h4>
      <p>${escapeHtml(o.description)}</p>
      <div class="meta">${cityName(o.city_slug)} · ${catName(o.category_slug)}${
    o.budget ? " · бюджет " + o.budget + " ₽" : ""
  }</div>
    </div>
    <h3>Отклики</h3>
    ${bids || '<p class="hint">Пока нет откликов</p>'}
  `;
  showTab("order");
}

function escapeHtml(s) {
  return String(s || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

async function loadMine() {
  const orders = await api("/api/my/orders");
  const bids = await api("/api/my/bids");
  document.getElementById("my-orders").innerHTML = orders.length
    ? orders
        .map(
          (o) =>
            `<div class="card" data-id="${o.id}"><h4>${escapeHtml(o.title)}</h4><div class="meta">${o.status} · откликов: ${
              o.bids_count
            }</div></div>`
        )
        .join("")
    : '<p class="hint">Заявок пока нет</p>';
  document.getElementById("my-bids").innerHTML = bids.length
    ? bids
        .map(
          (b) =>
            `<div class="card"><h4>${escapeHtml(b.order_title || "Заявка #" + b.order_id)}</h4><p>${escapeHtml(
              b.message
            )}</p><div class="meta">${b.status}</div></div>`
        )
        .join("")
    : '<p class="hint">Откликов пока нет</p>';
  document.querySelectorAll("#my-orders .card[data-id]").forEach((el) => {
    el.onclick = () => openOrder(el.getAttribute("data-id"));
  });
}

async function saveProfile() {
  await api("/api/me", {
    method: "PATCH",
    body: JSON.stringify({
      role: document.getElementById("prof-role").value,
      city_slug: document.getElementById("prof-city").value || null,
      bio: document.getElementById("prof-bio").value,
    }),
  });
  state.me = await api("/api/me");
  renderUser();
  alert("Сохранено");
}

function renderUser() {
  const m = state.me;
  document.getElementById("user-chip").textContent = m
    ? `${m.full_name || m.username || m.telegram_id} · ${m.role}`
    : "гость";
  if (m) {
    document.getElementById("prof-role").value = m.role || "customer";
    if (m.city_slug) document.getElementById("prof-city").value = m.city_slug;
    document.getElementById("prof-bio").value = m.bio || "";
  }
}

async function boot() {
  document.querySelectorAll(".tabs button").forEach((b) => {
    b.onclick = async () => {
      const name = b.getAttribute("data-tab");
      showTab(name);
      if (name === "feed") await loadFeed();
      if (name === "mine") await loadMine();
    };
  });
  document.getElementById("btn-back-feed").onclick = () => {
    showTab("feed");
    loadFeed();
  };
  document.getElementById("filter-city").onchange = loadFeed;
  document.getElementById("filter-cat").onchange = loadFeed;
  document.getElementById("btn-save-profile").onclick = () => saveProfile().catch((e) => alert(e.message));
  document.getElementById("btn-create").onclick = async () => {
    try {
      await api("/api/orders", {
        method: "POST",
        body: JSON.stringify({
          city_slug: document.getElementById("new-city").value,
          category_slug: document.getElementById("new-cat").value,
          title: document.getElementById("new-title").value,
          description: document.getElementById("new-desc").value,
          budget: document.getElementById("new-budget").value
            ? Number(document.getElementById("new-budget").value)
            : null,
        }),
      });
      alert("Заявка опубликована");
      document.getElementById("new-title").value = "";
      document.getElementById("new-desc").value = "";
      showTab("feed");
      await loadFeed();
    } catch (e) {
      alert(e.message);
    }
  };
  document.getElementById("btn-bid").onclick = async () => {
    try {
      await api("/api/orders/" + state.currentOrderId + "/bids", {
        method: "POST",
        body: JSON.stringify({
          message: document.getElementById("bid-msg").value,
          price: document.getElementById("bid-price").value
            ? Number(document.getElementById("bid-price").value)
            : null,
        }),
      });
      alert("Отклик отправлен (бесплатно)");
      document.getElementById("bid-msg").value = "";
      openOrder(state.currentOrderId);
    } catch (e) {
      alert(e.message);
    }
  };

  state.meta = await api("/api/meta");
  fillSelect(document.getElementById("filter-city"), state.meta.cities, true);
  fillSelect(document.getElementById("filter-cat"), state.meta.categories, true);
  fillSelect(document.getElementById("new-city"), state.meta.cities, false);
  fillSelect(document.getElementById("new-cat"), state.meta.categories, false);
  fillSelect(document.getElementById("prof-city"), state.meta.cities, false);
  state.me = await api("/api/me");
  renderUser();
  await loadFeed();
}

boot().catch((e) => {
  document.getElementById("orders-list").innerHTML =
    '<div class="card"><p>Ошибка загрузки: ' + escapeHtml(e.message) + "</p></div>";
});
