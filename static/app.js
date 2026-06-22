const COLOR_SWATCHES = [
  "#ff7f7f",
  "#ffbf7f",
  "#ffe17f",
  "#f8ff7f",
  "#c8ff7f",
  "#7ff58d",
  "#7ff3ff",
  "#7fb6ff",
  "#7f7fff",
  "#ef7fff",
  "#c87fbf",
  "#5e5e5e",
  "#9a9a9a",
  "#d6d6d6",
  "#f4f4f4",
];

const DEFAULT_TIERS = [
  ["S", "#ff7f7f"],
  ["A", "#ffbf7f"],
  ["B", "#ffe07a"],
  ["C", "#f6ff7a"],
  ["D", "#b9ff7a"],
  ["F", "#7ad7ff"],
];

const state = {
  board: null,
  saveTimer: null,
  draggingId: null,
  activeTierId: null,
  activeItemId: null,
  searchResults: [],
  searchBusy: false,
  searchSort: "released-desc",
  confirmResolver: null,
};

const elements = {
  status: document.getElementById("status"),
  titleInput: document.getElementById("titleInput"),
  searchInput: document.getElementById("searchInput"),
  searchBtn: document.getElementById("searchBtn"),
  searchResults: document.getElementById("searchResults"),
  searchSortSelect: document.getElementById("searchSortSelect"),
  addTierBtn: document.getElementById("addTierBtn"),
  newBoardBtn: document.getElementById("newBoardBtn"),
  saveBtn: document.getElementById("saveBtn"),
  exportBtn: document.getElementById("exportBtn"),
  importBtn: document.getElementById("importBtn"),
  fileInput: document.getElementById("fileInput"),
  tiersRoot: document.getElementById("tiersRoot"),
  benchRoot: document.getElementById("benchRoot"),
  notesInput: document.getElementById("notesInput"),
  tierModal: document.getElementById("tierModal"),
  tierModalTitle: document.getElementById("tierModalTitle"),
  tierLabelInput: document.getElementById("tierLabelInput"),
  colorRow: document.getElementById("colorRow"),
  addTierAboveBtn: document.getElementById("addTierAboveBtn"),
  addTierBelowBtn: document.getElementById("addTierBelowBtn"),
  clearTierBtn: document.getElementById("clearTierBtn"),
  deleteTierBtn: document.getElementById("deleteTierBtn"),
  itemModal: document.getElementById("itemModal"),
  itemModalTitle: document.getElementById("itemModalTitle"),
  itemPreviewThumb: document.getElementById("itemPreviewThumb"),
  itemPreviewMeta: document.getElementById("itemPreviewMeta"),
  itemLabelInput: document.getElementById("itemLabelInput"),
  itemDescription: document.getElementById("itemDescription"),
  itemRemoveBtn: document.getElementById("itemRemoveBtn"),
  confirmModal: document.getElementById("confirmModal"),
  confirmModalTitle: document.getElementById("confirmModalTitle"),
  confirmMessage: document.getElementById("confirmMessage"),
  confirmCancelBtn: document.getElementById("confirmCancelBtn"),
  confirmOkBtn: document.getElementById("confirmOkBtn"),
};

const itemTemplate = document.getElementById("itemTemplate");
const tierTemplate = document.getElementById("tierTemplate");

function uid(prefix) {
  return `${prefix}_${Math.random().toString(36).slice(2, 10)}`;
}

function normalizeHexColor(value, fallback = "#64748b") {
  const trimmed = String(value || "").trim();
  if (!/^#[0-9a-fA-F]{6}$/.test(trimmed)) return fallback;
  return trimmed.toLowerCase();
}

function escapeHtml(text) {
  return String(text)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function decodeHtmlEntities(str) {
  if (!str) return "";
  try {
    const doc = new DOMParser().parseFromString(str, "text/html");
    return doc.documentElement.textContent || "";
  } catch {
    return String(str);
  }
}

function formatReleaseDate(value) {
  if (!value) return "Unknown release";
  const date = new Date(`${value}T00:00:00`);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("ru-RU", {
    day: "numeric",
    month: "long",
    year: "numeric",
  }).format(date);
}

function formatPlatforms(platforms) {
  if (!Array.isArray(platforms) || platforms.length === 0) return "Platforms unknown";
  return platforms.join(" • ");
}

function placeholderThumb(label) {
  const safe = escapeHtml(label).slice(0, 18);
  const svg = `
    <svg xmlns="http://www.w3.org/2000/svg" width="256" height="256" viewBox="0 0 256 256">
      <defs>
        <linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stop-color="#5a4e6f"/>
          <stop offset="100%" stop-color="#17131d"/>
        </linearGradient>
      </defs>
      <rect width="256" height="256" rx="36" fill="url(#g)"/>
      <circle cx="86" cy="82" r="18" fill="#f2b96d" fill-opacity="0.85"/>
      <rect x="100" y="64" width="92" height="100" rx="24" fill="#ffffff" fill-opacity="0.08"/>
      <path d="M86 174c20-18 64-18 84 0" fill="none" stroke="#ffffff" stroke-opacity="0.7" stroke-width="10" stroke-linecap="round"/>
      <text x="50%" y="82%" text-anchor="middle" dominant-baseline="middle"
            fill="rgba(255,255,255,0.8)" font-family="Trebuchet MS, Segoe UI, sans-serif"
            font-size="20" font-weight="700">${safe}</text>
    </svg>`;
  return `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(svg)}`;
}

function makeTier(label, color) {
  return { id: uid("tier"), label, color };
}

function makeItem(label, imageUrl, extra = {}) {
  return {
    id: uid("item"),
    label,
    tier_id: null,
    image_url: imageUrl || placeholderThumb(label),
    rawg_id: extra.rawg_id ?? null,
    rawg_slug: extra.rawg_slug ?? null,
    platforms: extra.platforms ?? [],
    released: extra.released ?? "",
    rating: extra.rating ?? null,
    metacritic: extra.metacritic ?? null,
    description: extra.description ?? "",
    cache_ready: extra.cache_ready ?? false,
    genres: extra.genres ?? [],
  };
}

function defaultBoard() {
  return {
    title: "My Tier List",
    notes: "",
    tiers: DEFAULT_TIERS.map(([label, color]) => makeTier(label, color)),
    items: [],
  };
}

function cloneBoard(board) {
  return {
    title: typeof board.title === "string" ? board.title : "My Tier List",
    notes: typeof board.notes === "string" ? board.notes : "",
    tiers: Array.isArray(board.tiers)
      ? board.tiers.map((tier) => ({
          id: tier.id || uid("tier"),
          label: typeof tier.label === "string" ? tier.label : "Tier",
          color: normalizeHexColor(tier.color, "#64748b"),
        }))
      : [],
    items: Array.isArray(board.items)
      ? board.items.map((item) => {
          const rawImage = typeof item.image_url === "string" ? item.image_url : "";
          const isGenerated = rawImage.startsWith("data:image/svg+xml");
          return {
            id: item.id || uid("item"),
            label: typeof item.label === "string" ? item.label : "Item",
            tier_id: typeof item.tier_id === "string" ? item.tier_id : null,
            image_url: rawImage && !isGenerated ? rawImage : placeholderThumb(item.label || "Item"),
            rawg_id: item.rawg_id ?? null,
            rawg_slug: item.rawg_slug ?? null,
            platforms: Array.isArray(item.platforms) ? item.platforms : [],
            released: typeof item.released === "string" ? item.released : "",
            rating: item.rating ?? null,
            metacritic: item.metacritic ?? null,
            description: typeof item.description === "string" ? decodeHtmlEntities(item.description) : "",
            genres: Array.isArray(item.genres) ? item.genres : [],
            cache_ready: Boolean(item.cache_ready),
          };
        })
      : [],
  };
}

function setStatus(text, kind = "idle") {
  elements.status.textContent = text;
  elements.status.dataset.kind = kind;
}

function canUseApi() {
  return location.protocol === "http:" || location.protocol === "https:";
}

function loadLocalBoard() {
  try {
    const raw = localStorage.getItem("tier-maker.board.v1");
    if (!raw) return null;
    return cloneBoard(JSON.parse(raw));
  } catch {
    return null;
  }
}

function saveLocalBoard(board) {
  try {
    localStorage.setItem("tier-maker.board.v1", JSON.stringify(board));
  } catch {
    // Ignore storage failures.
  }
}

function saveSoon() {
  clearTimeout(state.saveTimer);
  state.saveTimer = setTimeout(() => {
    persistBoard(false);
  }, 250);
}

function itemsForTier(tierId) {
  return state.board.items.filter((item) => item.tier_id === tierId);
}

function tierById(tierId) {
  return state.board.tiers.find((tier) => tier.id === tierId) || null;
}

function sortValue(value, kind) {
  if (kind === "released") {
    const date = value ? new Date(`${value}T00:00:00`) : null;
    return date && !Number.isNaN(date.getTime()) ? date.getTime() : Number.NEGATIVE_INFINITY;
  }
  if (kind === "name") {
    return String(value || "").toLocaleLowerCase();
  }
  if (value == null || value === "") return Number.NEGATIVE_INFINITY;
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : Number.NEGATIVE_INFINITY;
}

function sortedSearchResults(results) {
  const [field, direction] = state.searchSort.split("-");
  const ascending = direction === "asc";
  return [...results].sort((left, right) => {
    const leftValue = sortValue(left[field], field);
    const rightValue = sortValue(right[field], field);

    let cmp = 0;
    if (typeof leftValue === "string" || typeof rightValue === "string") {
      cmp = String(leftValue).localeCompare(String(rightValue), undefined, { sensitivity: "base" });
    } else {
      cmp = leftValue - rightValue;
    }

    if (cmp === 0) {
      cmp = String(left.name || "").localeCompare(String(right.name || ""), undefined, { sensitivity: "base" });
    }
    return ascending ? cmp : -cmp;
  });
}

function exportFilename(title) {
  const cleaned = String(title || "tier-list")
    .replace(/[<>:"/\\|?*]/g, "")
    .replace(/\s+/g, " ")
    .trim();
  return `${cleaned || "tier-list"}.json`;
}

function showConfirmModal({ title = "Are you sure?", message, confirmLabel = "Confirm" }) {
  return new Promise((resolve) => {
    state.confirmResolver = resolve;
    elements.confirmModalTitle.textContent = title;
    elements.confirmMessage.textContent = message;
    elements.confirmOkBtn.textContent = confirmLabel;
    elements.confirmModal.classList.remove("hidden");
    elements.confirmModal.setAttribute("aria-hidden", "false");
    elements.confirmOkBtn.focus();
  });
}

function closeConfirmModal(result = false) {
  elements.confirmModal.classList.add("hidden");
  elements.confirmModal.setAttribute("aria-hidden", "true");
  const resolver = state.confirmResolver;
  state.confirmResolver = null;
  if (resolver) resolver(result);
}

function isDefaultBoard(board) {
  const defaultBoardState = defaultBoard();
  if (board.title !== defaultBoardState.title) return false;
  if (board.notes !== defaultBoardState.notes) return false;
  if (board.items.length !== 0) return false;
  if (board.tiers.length !== defaultBoardState.tiers.length) return false;
  return board.tiers.every((tier, index) => {
    const defaultTier = defaultBoardState.tiers[index];
    return tier.id === defaultTier.id && tier.label === defaultTier.label && tier.color === defaultTier.color;
  });
}

function itemById(itemId) {
  return state.board.items.find((item) => item.id === itemId) || null;
}

function render() {
  if (!state.board) return;

  elements.titleInput.value = state.board.title || "";
  elements.notesInput.value = state.board.notes || "";

  elements.tiersRoot.innerHTML = "";
  state.board.tiers.forEach((tier) => {
    const tierNode = tierTemplate.content.firstElementChild.cloneNode(true);
    const labelNode = tierNode.querySelector(".tier-label");
    const nameNode = tierNode.querySelector(".tier-name");
    const dropNode = tierNode.querySelector(".tier-drop");

    labelNode.style.background = tier.color;
    nameNode.textContent = tier.label;
    dropNode.dataset.tierId = tier.id;

    itemsForTier(tier.id).forEach((item) => dropNode.appendChild(renderItem(item, tier.id)));
    wireDropZone(dropNode, tier.id);

    tierNode.querySelector('[data-action="tier-settings"]').addEventListener("click", () => openTierModal(tier.id));
    tierNode.querySelector('[data-action="tier-up"]').addEventListener("click", () => moveTier(tier.id, -1));
    tierNode.querySelector('[data-action="tier-down"]').addEventListener("click", () => moveTier(tier.id, 1));

    elements.tiersRoot.appendChild(tierNode);
  });

  elements.benchRoot.innerHTML = "";
  itemsForTier(null).forEach((item) => elements.benchRoot.appendChild(renderItem(item, null)));
  wireDropZone(elements.benchRoot, null);

  renderSearchResults();
  if (state.activeTierId) renderTierModal();
  if (state.activeItemId) renderItemModal();
}

function renderItem(item, tierId) {
  const node = itemTemplate.content.firstElementChild.cloneNode(true);
  node.dataset.itemId = item.id;
  node.dataset.tierId = tierId ?? "";

  const thumb = node.querySelector(".item-thumb");
  thumb.src = item.image_url || placeholderThumb(item.label);
  thumb.alt = item.label;
  thumb.classList.toggle("placeholder", !item.image_url || item.image_url.startsWith("data:image/svg+xml"));
  // adapt thumbnail aspect based on actual image proportions (format, not resolution)
  const wrap = node.querySelector('.item-thumb-wrap');
  function applyAspect(img) {
    try {
      const ar = img.naturalWidth && img.naturalHeight ? img.naturalWidth / img.naturalHeight : 1;
      wrap.classList.remove('thumb-16x9','thumb-4x3','thumb-1x1','thumb-3x4');
      node.classList.remove('card-16x9','card-4x3','card-1x1','card-3x4');
      if (ar >= 1.6) {
        wrap.classList.add('thumb-16x9');
        node.classList.add('card-16x9');
      } else if (ar >= 1.3) {
        wrap.classList.add('thumb-4x3');
        node.classList.add('card-4x3');
      } else if (ar >= 0.85) {
        wrap.classList.add('thumb-1x1');
        node.classList.add('card-1x1');
      } else {
        wrap.classList.add('thumb-3x4');
        node.classList.add('card-3x4');
      }
    } catch (e) {
      wrap.classList.add('thumb-1x1');
    }
  }
  if (thumb.complete) applyAspect(thumb);
  else thumb.addEventListener('load', () => applyAspect(thumb));
  node.querySelector(".item-label").textContent = item.label;

  const removeBtn = node.querySelector('[data-action="delete"]');
  const onShelf = tierId == null;
  removeBtn.title = onShelf ? "Delete permanently" : "Move to shelf";
  removeBtn.setAttribute("aria-label", removeBtn.title);

  node.querySelector('[data-action="rename"]').addEventListener("click", () => openItemModal(item.id));
  removeBtn.addEventListener("click", () => void removeItem(item.id));

  node.addEventListener("dragstart", (event) => {
    state.draggingId = item.id;
    node.classList.add("dragging");
    event.dataTransfer.effectAllowed = "move";
    event.dataTransfer.setData("text/plain", item.id);
  });

  node.addEventListener("dragend", () => {
    state.draggingId = null;
    node.classList.remove("dragging");
    document.querySelectorAll(".drag-over").forEach((el) => el.classList.remove("drag-over"));
  });

  return node;
}

function wireDropZone(zone, tierId) {
  if (zone.dataset.dropBound === "1") return;
  zone.dataset.dropBound = "1";

  zone.addEventListener("dragover", (event) => {
    event.preventDefault();
    zone.classList.add("drag-over");
  });

  zone.addEventListener("dragleave", (event) => {
    if (!zone.contains(event.relatedTarget)) {
      zone.classList.remove("drag-over");
    }
  });

  zone.addEventListener("drop", (event) => {
    event.preventDefault();
    zone.classList.remove("drag-over");
    const itemId = event.dataTransfer.getData("text/plain") || state.draggingId;
    if (!itemId) return;
    dropItemIntoZone(zone, tierId, itemId, event.clientX, event.clientY);
  });
}

function dropItemIntoZone(zone, targetTierId, itemId, clientX, clientY) {
  const cards = [...zone.querySelectorAll(".item-card")].filter((card) => card.dataset.itemId !== itemId);
  if (cards.length === 0) {
    moveItem(itemId, targetTierId);
    return;
  }

  let closest = null;
  let closestDistance = Number.POSITIVE_INFINITY;
  for (const card of cards) {
    const rect = card.getBoundingClientRect();
    const centerX = rect.left + rect.width / 2;
    const centerY = rect.top + rect.height / 2;
    const distance = Math.hypot(clientX - centerX, clientY - centerY);
    if (distance < closestDistance) {
      closestDistance = distance;
      closest = card;
    }
  }

  if (!closest) {
    moveItem(itemId, targetTierId);
    return;
  }

  const rect = closest.getBoundingClientRect();
  const before = clientX < rect.left + rect.width / 2 || (clientY < rect.top + rect.height / 2 && clientX <= rect.left + rect.width / 2);
  moveItem(itemId, targetTierId, closest.dataset.itemId, before);
}

function moveItem(itemId, targetTierId, referenceId = null, before = false) {
  const items = state.board.items;
  const index = items.findIndex((item) => item.id === itemId);
  if (index === -1) return;

  const [item] = items.splice(index, 1);
  item.tier_id = targetTierId;

  let insertAt = items.length;
  if (referenceId) {
    const refIndex = items.findIndex((candidate) => candidate.id === referenceId);
    if (refIndex >= 0) insertAt = before ? refIndex : refIndex + 1;
  } else {
    let lastIndex = -1;
    for (let i = 0; i < items.length; i += 1) {
      if (items[i].tier_id === targetTierId) lastIndex = i;
    }
    insertAt = lastIndex >= 0 ? lastIndex + 1 : items.length;
  }

  items.splice(insertAt, 0, item);
  render();
  saveSoon();
}

async function addGameItem(game) {
  if (!canUseApi()) {
    setStatus("Run via python main.py to add games from RAWG", "error");
    return;
  }

  setStatus(`Caching ${game.name}…`);
  try {
    const response = await fetch("/api/rawg/cache", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ rawg_id: game.id }),
    });
    const payload = await response.json();
    if (!response.ok || !payload.ok) {
      throw new Error(payload.error || "Cache failed");
    }

    const cached = payload.game;
    const imageUrl = cached.image_url || placeholderThumb(cached.name);
    const item = makeItem(cached.name, imageUrl, {
      rawg_id: cached.id,
      rawg_slug: cached.slug,
      platforms: Array.isArray(cached.platforms) ? cached.platforms : [],
      released: cached.released || "",
      rating: cached.rating ?? null,
      metacritic: cached.metacritic ?? null,
      description: decodeHtmlEntities(cached.description || ""),
      cache_ready: true,
      genres: Array.isArray(cached.genres) ? cached.genres : [],
    });
    state.board.items.push(item);
    state.searchResults = [];
    elements.searchInput.value = "";
    render();
    saveSoon();
    setStatus(`Added ${cached.name} to shelf`);
  } catch (error) {
    setStatus(`Failed to cache ${game.name}: ${error.message}`, "error");
  }
}

async function searchGames() {
  const query = elements.searchInput.value.trim();
  if (!query) {
    state.searchResults = [];
    renderSearchResults();
    return;
  }

  if (!canUseApi()) {
    setStatus("Run via python main.py to search RAWG", "error");
    return;
  }

  state.searchBusy = true;
  renderSearchResults();

  try {
    const response = await fetch(`/api/rawg/search?q=${encodeURIComponent(query)}`);
    const payload = await response.json();
    if (!response.ok || !payload.ok) {
      throw new Error(payload.error || "Search failed");
    }
    state.searchResults = payload.results || [];
    setStatus(`Found ${state.searchResults.length} games`);
  } catch (error) {
    state.searchResults = [];
    setStatus(`Search failed: ${error.message}`, "error");
  } finally {
    state.searchBusy = false;
    renderSearchResults();
  }
}

function renderSearchResults() {
  const query = elements.searchInput.value.trim();
  const results = state.searchResults;

  if (state.searchBusy) {
    elements.searchResults.classList.remove("hidden");
    elements.searchResults.innerHTML = `<div class="search-result"><div class="meta">Searching RAWG...</div></div>`;
    return;
  }

  if (!query || results.length === 0) {
    elements.searchResults.innerHTML = "";
    elements.searchResults.classList.add("hidden");
    return;
  }

  elements.searchResults.classList.remove("hidden");
  const sorted = sortedSearchResults(results);
  elements.searchResults.innerHTML = sorted
    .map((game) => {
      const image = game.background_image || placeholderThumb(game.name);
      const meta = [
        formatReleaseDate(game.released),
        game.metacritic ? `Metacritic ${game.metacritic}` : "",
        formatPlatforms(game.platforms),
      ]
        .filter(Boolean)
        .join(" • ");

      return `
        <button type="button" class="search-result" data-game-id="${game.id}">
          <img src="${escapeHtml(image)}" alt="${escapeHtml(game.name)}">
          <div>
            <strong>${escapeHtml(game.name)}</strong>
            <div class="meta">${escapeHtml(meta || "Click to add to the shelf")}</div>
          </div>
        </button>
      `;
    })
    .join("");
}

// Custom select control logic for Sort results
const SORT_OPTIONS = [
  ["released-desc", "Release date (newest first)"],
  ["released-asc", "Release date (oldest first)"],
  ["name-asc", "Name (A → Z)"],
  ["name-desc", "Name (Z → A)"],
  ["rating-desc", "Rating (highest first)"],
  ["rating-asc", "Rating (lowest first)"],
  ["metacritic-desc", "Metacritic (highest first)"],
  ["metacritic-asc", "Metacritic (lowest first)"],
  ["added-desc", "Added to RAWG (newest first)"],
  ["added-asc", "Added to RAWG (oldest first)"],
  ["created-desc", "Created in RAWG (newest first)"],
  ["created-asc", "Created in RAWG (oldest first)"],
  ["updated-desc", "Updated (newest first)"],
  ["updated-asc", "Updated (oldest first)"],
];

function initCustomSelect() {
  const ctrl = document.getElementById("searchSortCustom");
  if (!ctrl) return;
  const toggle = ctrl.querySelector(".custom-select-toggle");
  const list = ctrl.querySelector(".custom-select-list");
  const label = ctrl.querySelector(".custom-select-label");

  function close() {
    toggle.setAttribute("aria-expanded", "false");
    list.classList.remove("open");
    list.setAttribute("aria-hidden", "true");
  }
  function open() {
    toggle.setAttribute("aria-expanded", "true");
    list.classList.add("open");
    list.setAttribute("aria-hidden", "false");
  }

  toggle.addEventListener("click", (e) => {
    const expanded = toggle.getAttribute("aria-expanded") === "true";
    if (expanded) close();
    else open();
  });

  list.addEventListener("click", (e) => {
    const li = e.target.closest("li[role='option']");
    if (!li) return;
    const val = li.dataset.value;
    const text = li.textContent.trim();
    ctrl.dataset.value = val;
    label.textContent = text;
    state.searchSort = val;
    renderSearchResults();
    close();
  });

  document.addEventListener("click", (e) => {
    if (!ctrl.contains(e.target)) close();
  });
}

function addTier() {
  const tier = makeTier("New", "#64748b");
  state.board.tiers.push(tier);
  state.activeTierId = tier.id;
  render();
  openTierModal(tier.id);
  saveSoon();
}

function moveTier(tierId, direction) {
  const index = state.board.tiers.findIndex((tier) => tier.id === tierId);
  const nextIndex = index + direction;
  if (index < 0 || nextIndex < 0 || nextIndex >= state.board.tiers.length) return;
  [state.board.tiers[index], state.board.tiers[nextIndex]] = [state.board.tiers[nextIndex], state.board.tiers[index]];
  render();
  saveSoon();
}

function openItemModal(itemId) {
  state.activeItemId = itemId;
  renderItemModal();
  elements.itemModal.classList.remove("hidden");
  elements.itemModal.setAttribute("aria-hidden", "false");
  elements.itemLabelInput.focus();
  elements.itemLabelInput.select();
}

function closeItemModal() {
  state.activeItemId = null;
  elements.itemModal.classList.add("hidden");
  elements.itemModal.setAttribute("aria-hidden", "true");
}

function renderItemModal() {
  const item = itemById(state.activeItemId);
  if (!item) {
    closeItemModal();
    return;
  }

  elements.itemModalTitle.textContent = `Edit ${item.label}`;
  elements.itemLabelInput.value = item.label;
  elements.itemPreviewThumb.src = item.image_url || placeholderThumb(item.label);
  elements.itemPreviewThumb.alt = item.label;
  elements.itemPreviewThumb.classList.toggle(
    "placeholder",
    !item.image_url || item.image_url.startsWith("data:image/svg+xml"),
  );
  // apply aspect class to modal preview image
  function applyPreviewAspect(img) {
    try {
      const ar = img.naturalWidth && img.naturalHeight ? img.naturalWidth / img.naturalHeight : 1;
      img.classList.remove('thumb-16x9','thumb-4x3','thumb-1x1','thumb-3x4');
      if (ar >= 1.6) img.classList.add('thumb-16x9');
      else if (ar >= 1.3) img.classList.add('thumb-4x3');
      else if (ar >= 0.85) img.classList.add('thumb-1x1');
      else img.classList.add('thumb-3x4');
    } catch (e) {
      img.classList.add('thumb-1x1');
    }
  }
  if (elements.itemPreviewThumb.complete) applyPreviewAspect(elements.itemPreviewThumb);
  else elements.itemPreviewThumb.addEventListener('load', () => applyPreviewAspect(elements.itemPreviewThumb));

  const metaParts = [
    formatReleaseDate(item.released),
    item.metacritic ? `Metacritic ${item.metacritic}` : "",
    formatPlatforms(item.platforms),
  ].filter(Boolean);
  if (Array.isArray(item.genres) && item.genres.length > 0) {
    metaParts.push(item.genres.join(", "));
  }
  elements.itemPreviewMeta.textContent = metaParts.join(" • ") || "No extra metadata";
  elements.itemDescription.textContent = item.description?.trim()
    ? item.description
    : item.rawg_id
      ? "Description is not cached yet."
      : "No RAWG description for this card.";

  const onShelf = item.tier_id == null;
  elements.itemRemoveBtn.textContent = onShelf ? "Delete permanently" : "Return to shelf";
}

async function removeItem(itemId) {
  const item = itemById(itemId);
  if (!item) return;

  if (item.tier_id != null) {
    item.tier_id = null;
    if (state.activeItemId === itemId) renderItemModal();
    render();
    saveSoon();
    return;
  }

  const confirmed = await showConfirmModal({
    title: "Delete card",
    message: `Delete ${item.label} permanently? This cannot be undone.`,
    confirmLabel: "Delete permanently",
  });
  if (!confirmed) return;

  state.board.items = state.board.items.filter((entry) => entry.id !== itemId);
  if (state.activeItemId === itemId) closeItemModal();
  render();
  saveSoon();
}

function openTierModal(tierId) {
  state.activeTierId = tierId;
  renderTierModal();
  elements.tierModal.classList.remove("hidden");
  elements.tierModal.setAttribute("aria-hidden", "false");
  elements.tierLabelInput.focus();
}

function closeTierModal() {
  state.activeTierId = null;
  elements.tierModal.classList.add("hidden");
  elements.tierModal.setAttribute("aria-hidden", "true");
}

function renderTierModal() {
  const tier = tierById(state.activeTierId);
  if (!tier) {
    closeTierModal();
    return;
  }

  elements.tierModalTitle.textContent = `Edit ${tier.label}`;
  elements.tierLabelInput.value = tier.label;
  elements.colorRow.innerHTML = "";

  COLOR_SWATCHES.forEach((color) => {
    const swatch = document.createElement("button");
    swatch.type = "button";
    swatch.className = "swatch";
    swatch.style.background = color;
    swatch.title = color;
    swatch.addEventListener("click", () => {
      tier.color = color;
      render();
      saveSoon();
      renderTierModal();
    });
    elements.colorRow.appendChild(swatch);
  });
}

function clearTierItems(tierId) {
  state.board.items.forEach((item) => {
    if (item.tier_id === tierId) item.tier_id = null;
  });
}

async function deleteTier(tierId) {
  const index = state.board.tiers.findIndex((tier) => tier.id === tierId);
  if (index === -1) return;
  const tier = state.board.tiers[index];
  const confirmed = await showConfirmModal({
    title: "Delete row",
    message: `Delete ${tier.label}? Items on this row will return to the shelf.`,
    confirmLabel: "Delete row",
  });
  if (!confirmed) return;
  clearTierItems(tierId);
  state.board.tiers.splice(index, 1);
  closeTierModal();
  render();
  saveSoon();
}

function addTierRelative(tierId, offset) {
  const index = state.board.tiers.findIndex((tier) => tier.id === tierId);
  if (index === -1) return;
  const tier = makeTier("New", "#64748b");
  const targetIndex = Math.max(0, Math.min(state.board.tiers.length, index + offset));
  state.board.tiers.splice(targetIndex, 0, tier);
  state.activeTierId = tier.id;
  render();
  openTierModal(tier.id);
  saveSoon();
}

function bindEvents() {
  elements.titleInput.addEventListener("input", () => {
    state.board.title = elements.titleInput.value;
    saveSoon();
  });

  elements.notesInput.addEventListener("input", () => {
    state.board.notes = elements.notesInput.value;
    saveSoon();
  });

  elements.searchBtn.addEventListener("click", searchGames);
  // initialize custom select
  initCustomSelect();
  // sync initial value
  const c = document.getElementById("searchSortCustom");
  if (c) {
    const labelEl = c.querySelector('.custom-select-label');
    const opt = SORT_OPTIONS.find((o) => o[0] === state.searchSort) || SORT_OPTIONS[0];
    c.dataset.value = state.searchSort;
    if (labelEl) labelEl.textContent = opt[1];
  }
  elements.searchInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter") searchGames();
    if (event.key === "Escape") {
      state.searchResults = [];
      renderSearchResults();
    }
  });

  elements.searchResults.addEventListener("click", (event) => {
    const button = event.target.closest("button[data-game-id]");
    if (!button) return;
    const game = state.searchResults.find((entry) => String(entry.id) === button.dataset.gameId);
    if (!game) return;
    void addGameItem(game);
  });

  elements.addTierBtn.addEventListener("click", addTier);
  if (elements.newBoardBtn) elements.newBoardBtn.addEventListener("click", resetBoard);
  elements.saveBtn.addEventListener("click", () => persistBoard(true));
  elements.exportBtn.addEventListener("click", exportBoard);
  elements.importBtn.addEventListener("click", () => elements.fileInput.click());
  elements.fileInput.addEventListener("change", async () => {
    const [file] = elements.fileInput.files || [];
    if (file) {
      const hasExistingBoard = !isDefaultBoard(state.board);
      if (hasExistingBoard) {
        const confirmed = await showConfirmModal({
          title: "Перезаписать текущий тирлист?",
          message: "Текущий тирлист будет заменён новым. Экспортируйте его, если хотите сохранить копию.",
          confirmLabel: "Продолжить",
        });
        if (!confirmed) {
          elements.fileInput.value = "";
          return;
        }
      }

      // if .tier, upload to server for import; otherwise treat as JSON board
      if (file.name && file.name.toLowerCase().endsWith(".tier")) {
        const fd = new FormData();
        fd.append("file", file);
        try {
          const resp = await fetch("/api/import_tier", { method: "POST", body: fd });
          const payload = await resp.json();
          if (!resp.ok || !payload.ok) throw new Error(payload.error || "Import failed");
          state.board = cloneBoard(payload.board || payload);
          saveLocalBoard(state.board);
          render();
          await persistBoard(true);
          setStatus("Imported .tier archive");
        } catch (e) {
          setStatus(`Import failed: ${e.message}`, "error");
        }
      } else {
        if (file) await importBoard(file);
      }
    }
    elements.fileInput.value = "";
  });

  elements.tierLabelInput.addEventListener("input", () => {
    const tier = tierById(state.activeTierId);
    if (!tier) return;
    tier.label = elements.tierLabelInput.value;
    render();
    saveSoon();
  });

  elements.addTierAboveBtn.addEventListener("click", () => {
    if (state.activeTierId) addTierRelative(state.activeTierId, 0);
  });

  elements.addTierBelowBtn.addEventListener("click", () => {
    if (state.activeTierId) addTierRelative(state.activeTierId, 1);
  });

  elements.clearTierBtn.addEventListener("click", () => {
    if (!state.activeTierId) return;
    clearTierItems(state.activeTierId);
    render();
    saveSoon();
  });

  elements.deleteTierBtn.addEventListener("click", () => {
    if (state.activeTierId) void deleteTier(state.activeTierId);
  });

  elements.itemLabelInput.addEventListener("input", () => {
    const item = itemById(state.activeItemId);
    if (!item) return;
    item.label = elements.itemLabelInput.value;
    render();
    saveSoon();
    renderItemModal();
  });

  elements.itemRemoveBtn.addEventListener("click", () => {
    if (state.activeItemId) void removeItem(state.activeItemId);
  });

  elements.confirmCancelBtn.addEventListener("click", () => closeConfirmModal(false));
  elements.confirmOkBtn.addEventListener("click", () => closeConfirmModal(true));
  elements.confirmModal.addEventListener("click", (event) => {
    if (event.target === elements.confirmModal || event.target.matches("[data-action='close-confirm-modal']")) {
      closeConfirmModal(false);
    }
  });

  elements.itemModal.addEventListener("click", (event) => {
    if (event.target === elements.itemModal || event.target.matches("[data-action='close-item-modal']")) {
      closeItemModal();
    }
  });

  elements.tierModal.addEventListener("click", (event) => {
    if (event.target === elements.tierModal || event.target.matches("[data-action='close-modal']")) {
      closeTierModal();
    }
  });

  document.addEventListener("keydown", (event) => {
    if (event.key !== "Escape") return;
    if (state.confirmResolver) closeConfirmModal(false);
    else if (state.activeItemId) closeItemModal();
    else if (state.activeTierId) closeTierModal();
  });
}

async function persistBoard(showMessage = true) {
  if (!state.board) return;
  saveLocalBoard(state.board);

  if (canUseApi()) {
    try {
      const response = await fetch("/api/state", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(state.board),
      });
      const payload = await response.json();
      if (!response.ok || !payload.ok) {
        throw new Error(payload.error || "Save failed");
      }
      state.board = cloneBoard(payload.board);
      if (showMessage) setStatus(`Saved to ${payload.save_path || "board.json"}`);
      return;
    } catch (error) {
      if (showMessage) setStatus(`Saved to browser storage; server unavailable: ${error.message}`, "error");
      return;
    }
  }

  if (showMessage) setStatus("Saved to browser storage only");
}

async function resetBoard() {
  if (!confirm("Create a fresh board? Current changes will be replaced.")) return;
  state.board = defaultBoard();
  state.searchResults = [];
  closeTierModal();
  closeItemModal();
  render();
  await persistBoard(true);
}

async function importBoard(file) {
  try {
    if (!isDefaultBoard(state.board)) {
      const confirmed = await showConfirmModal({
        title: "Перезаписать текущий тирлист?",
        message: "Текущий тирлист будет заменён новым. Экспортируйте его, если хотите сохранить копию.",
        confirmLabel: "Продолжить",
      });
      if (!confirmed) return;
    }

    const parsed = cloneBoard(JSON.parse(await file.text()));
    state.board = parsed;
    saveLocalBoard(parsed);
    render();
    await persistBoard(true);
    setStatus("Imported");
  } catch (error) {
    setStatus(`Import failed: ${error.message}`, "error");
  }
}

async function exportBoard() {
  // Request server to build a .tier archive (zip) containing board + images
  try {
    const response = await fetch(`/api/export_tier`);
    if (!response.ok) throw new Error(`Export failed: ${response.statusText}`);
    const blob = await response.blob();
    const filename = `${exportFilename(state.board.title).replace(/\.json$/, "")}.tier`;
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
    setStatus(`Export prepared: ${filename}`);
  } catch (err) {
    setStatus(String(err), "error");
  }
}

async function boot() {
  bindEvents();

  if (canUseApi()) {
    try {
      const response = await fetch("/api/state");
      const payload = await response.json();
      state.board = cloneBoard(payload);
      saveLocalBoard(state.board);
      render();
      setStatus("Ready");
      return;
    } catch {
      // Fall through to local storage.
    }
  }

  const local = loadLocalBoard();
  if (local) {
    state.board = local;
    render();
    setStatus(location.protocol === "file:" ? "Loaded from browser storage" : "Loaded local draft");
    return;
  }

  state.board = defaultBoard();
  render();
  setStatus("Ready");
}

boot();

