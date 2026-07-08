const state = {
  people: [],
  checkins: [],
  logs: [],
  captures: {
    photo: { stream: null, blob: null },
    recognize: { stream: null, blob: null },
  },
};

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => Array.from(document.querySelectorAll(selector));

function toast(message, type = "success") {
  const element = $("#toast");
  element.textContent = message;
  element.className = `toast ${type}`;
  element.hidden = false;
  window.clearTimeout(toast.timer);
  toast.timer = window.setTimeout(() => {
    element.hidden = true;
  }, 4200);
}

async function requestJson(url, options = {}) {
  const response = await fetch(url, options);
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.detail || "Erro ao conectar com a API.");
  }
  return data;
}

function emptyRow(columns, message) {
  return `<tr><td colspan="${columns}" class="empty">${message}</td></tr>`;
}

function formatDate(value) {
  if (!value) return "-";
  return value.replace("T", " ");
}

function formatConfidence(value) {
  if (value === null || value === undefined || value === "") return "-";
  return Number(value).toFixed(4);
}

function captureElements(mode) {
  return {
    video: $(`#${mode}Video`),
    canvas: $(`#${mode}Canvas`),
    preview: $(`#${mode}Preview`),
    input: $(`.capture-box[data-capture="${mode}"] input[type="file"]`),
  };
}

async function startCamera(mode) {
  const current = state.captures[mode];
  const { video, input } = captureElements(mode);

  if (!navigator.mediaDevices?.getUserMedia) {
    input.click();
    toast("Seu navegador bloqueou a câmera direta. Use a câmera aberta pelo seletor de imagem.", "warn");
    return;
  }

  if (current.stream) {
    current.stream.getTracks().forEach((track) => track.stop());
  }

  current.stream = await navigator.mediaDevices.getUserMedia({
    video: { facingMode: "user" },
    audio: false,
  });
  video.srcObject = current.stream;
  video.classList.add("is-active");
}

function captureFromCamera(mode) {
  const current = state.captures[mode];
  const { video, canvas, preview, input } = captureElements(mode);

  if (!current.stream || video.videoWidth === 0) {
    throw new Error("Abra a câmera antes de tirar a foto.");
  }

  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;
  canvas.getContext("2d").drawImage(video, 0, 0, canvas.width, canvas.height);

  canvas.toBlob((blob) => {
    current.blob = blob;
    input.value = "";
    preview.src = URL.createObjectURL(blob);
    preview.hidden = false;
  }, "image/jpeg", 0.92);
}

function setUploadPreview(mode) {
  const current = state.captures[mode];
  const { input, preview } = captureElements(mode);
  const file = input.files[0];

  current.blob = null;
  if (!file) {
    preview.hidden = true;
    preview.removeAttribute("src");
    return;
  }

  preview.src = URL.createObjectURL(file);
  preview.hidden = false;
}

function selectedCapture(mode) {
  const { input } = captureElements(mode);
  return state.captures[mode].blob || input.files[0] || null;
}

function renderRecognitionResult(data) {
  const result = $("#recognizeResult");
  const recognized = Boolean(data.recognized);
  result.className = `result-box ${recognized ? "success" : "error"}`;
  result.innerHTML = `
    <strong>${data.message || (recognized ? "Pessoa reconhecida." : "Pessoa não reconhecida.")}</strong>
    <dl>
      <div><dt>Status</dt><dd>${recognized ? "Reconhecido" : "Não reconhecido"}</dd></div>
      <div><dt>ID</dt><dd>${data.person_id || "-"}</dd></div>
      <div><dt>Nome</dt><dd>${data.name || "-"}</dd></div>
      <div><dt>Unidade</dt><dd>${data.unit || "-"}</dd></div>
      <div><dt>Função</dt><dd>${data.role || "-"}</dd></div>
      <div><dt>Confiança</dt><dd>${formatConfidence(data.confidence)}</dd></div>
    </dl>
  `;
}

function renderPeople() {
  const rows = $("#peopleRows");
  const photoSelect = $("#photoPersonSelect");

  rows.innerHTML = state.people.length
    ? state.people.map((person) => `
        <tr>
          <td>${person.person_id}</td>
          <td>${person.name}</td>
          <td>${person.unit || "-"}</td>
          <td>${person.role || "-"}</td>
          <td><span class="badge">${person.photos_count || 0}</span></td>
        </tr>
      `).join("")
    : emptyRow(5, "Nenhuma pessoa cadastrada.");

  const options = state.people.map((person) => (
    `<option value="${person.person_id}">${person.person_id} - ${person.name}</option>`
  )).join("");
  photoSelect.innerHTML = options || '<option value="">Cadastre uma pessoa primeiro</option>';
  renderManualOptions();
}

function renderManualOptions() {
  const search = $("#manualSearch").value.trim().toLowerCase();
  const filtered = state.people.filter((person) => {
    const text = `${person.person_id} ${person.name}`.toLowerCase();
    return text.includes(search);
  });
  $("#manualPersonSelect").innerHTML = filtered.length
    ? filtered.map((person) => `<option value="${person.person_id}">${person.person_id} - ${person.name}</option>`).join("")
    : '<option value="">Pessoa não encontrada</option>';
}

function renderCheckins() {
  $("#checkinRows").innerHTML = state.checkins.length
    ? state.checkins.map((item) => `
        <tr>
          <td>
            <button class="danger-button" type="button" data-checkin-delete="${item.id}">
              Remover
            </button>
          </td>
          <td>${item.name}</td>
          <td>${item.person_id}</td>
          <td><span class="badge ${item.method === "face" ? "ok" : ""}">${item.method}</span></td>
          <td>${formatConfidence(item.confidence)}</td>
          <td>${item.already_checked_in ? "Sim" : "Não"}</td>
          <td>${formatDate(item.checked_in_at)}</td>
        </tr>
      `).join("")
    : emptyRow(7, "Nenhum credenciamento registrado.");
}

function logClass(action) {
  if ((action || "").includes("ERROR")) return "danger";
  if ((action || "").includes("CHECKIN")) return "ok";
  return "";
}

function renderLogs() {
  $("#logRows").innerHTML = state.logs.length
    ? state.logs.map((item) => `
        <tr>
          <td><span class="badge ${logClass(item.action)}">${item.action}</span></td>
          <td>${item.person_id || "-"}</td>
          <td>${item.message || "-"}</td>
          <td>${formatDate(item.created_at)}</td>
        </tr>
      `).join("")
    : emptyRow(4, "Nenhum log registrado.");
}

function renderDashboard(data) {
  const stats = data.stats || {};
  $("#metricPeople").textContent = stats.people || 0;
  $("#metricPhotos").textContent = stats.photos || 0;
  $("#metricCheckins").textContent = stats.checkins || 0;
  $("#metricMethods").textContent = `${stats.face_checkins || 0} / ${stats.manual_checkins || 0}`;

  $("#latestCheckins").innerHTML = (data.latest_checkins || []).length
    ? data.latest_checkins.map((item) => `
        <article><strong>${item.name}</strong><span>${item.method} - ${formatDate(item.checked_in_at)}</span></article>
      `).join("")
    : '<p class="empty-text">Sem credenciamentos.</p>';

  $("#latestLogs").innerHTML = (data.latest_logs || []).length
    ? data.latest_logs.map((item) => `
        <article><strong>${item.action}</strong><span>${item.message || "-"}</span></article>
      `).join("")
    : '<p class="empty-text">Sem logs.</p>';
}

async function loadPeople() {
  const data = await requestJson("/people");
  state.people = data.people || [];
  renderPeople();
}

async function loadCheckins() {
  const data = await requestJson("/checkins");
  state.checkins = data.checkins || [];
  renderCheckins();
}

async function loadLogs() {
  const data = await requestJson("/logs");
  state.logs = data.logs || [];
  renderLogs();
}

async function loadDashboard() {
  const data = await requestJson("/dashboard");
  renderDashboard(data);
}

async function refreshAll() {
  try {
    await Promise.all([loadPeople(), loadCheckins(), loadLogs(), loadDashboard()]);
  } catch (error) {
    toast(error.message, "error");
  }
}

function setPage(page) {
  $$(".nav-item").forEach((item) => item.classList.toggle("is-active", item.dataset.page === page));
  $$(".page").forEach((panel) => panel.classList.toggle("is-active", panel.dataset.pagePanel === page));
}

$$(".nav-item").forEach((item) => {
  item.addEventListener("click", () => setPage(item.dataset.page));
});

$$('[data-action="refresh"]').forEach((button) => {
  button.addEventListener("click", refreshAll);
});

$("#personForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  try {
    await requestJson("/people", { method: "POST", body: new FormData(form) });
    form.reset();
    toast("Pessoa cadastrada com sucesso.");
    await refreshAll();
  } catch (error) {
    toast(error.message, "error");
  }
});

$("#photoForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const data = new FormData(form);
  const personId = data.get("person_id");
  const image = selectedCapture("photo");

  if (!image) {
    toast("Selecione uma imagem ou tire uma foto.", "error");
    return;
  }

  const payload = new FormData();
  payload.append("image", image, "foto-cadastro.jpg");

  try {
    await requestJson(`/people/${encodeURIComponent(personId)}/photo`, { method: "POST", body: payload });
    form.reset();
    state.captures.photo.blob = null;
    $("#photoPreview").hidden = true;
    $("#photoPreview").removeAttribute("src");
    toast("Foto cadastrada e reconhecimento facial preparado.");
    await refreshAll();
  } catch (error) {
    toast(error.message, "error");
  }
});

$("#manualForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  try {
    const data = await requestJson("/checkin-manual", { method: "POST", body: new FormData(form) });
    toast(data.message || "Check-in manual realizado com sucesso.", data.already_checked_in ? "warn" : "success");
    await refreshAll();
  } catch (error) {
    toast(error.message, "error");
  }
});

$("#recognizeForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const image = selectedCapture("recognize");

  if (!image) {
    toast("Selecione uma imagem ou tire uma foto para testar.", "error");
    return;
  }

  const payload = new FormData();
  payload.append("image", image, "teste-reconhecimento.jpg");

  try {
    const data = await requestJson("/recognize", { method: "POST", body: payload });
    renderRecognitionResult(data);
    toast(data.message || "Teste concluído.", data.recognized ? "success" : "warn");
  } catch (error) {
    toast(error.message, "error");
  }
});

$("#manualSearch").addEventListener("input", renderManualOptions);

$("#checkinRows").addEventListener("click", async (event) => {
  const button = event.target.closest("[data-checkin-delete]");
  if (!button) return;

  const checkinId = button.dataset.checkinDelete;
  const checkin = state.checkins.find((item) => String(item.id) === checkinId);
  const label = checkin ? `${checkin.name} (${checkin.person_id})` : `#${checkinId}`;

  if (!window.confirm(`Remover o check-in de ${label}?`)) return;

  button.disabled = true;
  try {
    const data = await requestJson(`/checkins/${encodeURIComponent(checkinId)}`, { method: "DELETE" });
    toast(data.message || "Check-in removido com sucesso.");
    await refreshAll();
  } catch (error) {
    button.disabled = false;
    toast(error.message, "error");
  }
});

$$("[data-camera-start]").forEach((button) => {
  button.addEventListener("click", async () => {
    try {
      await startCamera(button.dataset.cameraStart);
    } catch (error) {
      toast(error.message, "error");
    }
  });
});

$$("[data-camera-capture]").forEach((button) => {
  button.addEventListener("click", () => {
    try {
      captureFromCamera(button.dataset.cameraCapture);
    } catch (error) {
      toast(error.message, "error");
    }
  });
});

$$(".capture-box input[type='file']").forEach((input) => {
  input.addEventListener("change", () => setUploadPreview(input.closest(".capture-box").dataset.capture));
});

refreshAll();
