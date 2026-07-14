const state = {
  units: [],
  people: [],
  checkins: [],
  logs: [],
  editingPersonId: null,
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
  const status = data.status || (recognized ? "recognized" : "not_recognized");
  result.innerHTML = `
    <strong>${data.message || (recognized ? "Pessoa reconhecida." : "Pessoa não reconhecida.")}</strong>
    <dl>
      <div><dt>Status</dt><dd>${status}</dd></div>
      <div><dt>Rostos</dt><dd>${data.face_count ?? "-"}</dd></div>
      <div><dt>Reconhecido</dt><dd>${recognized ? "Sim" : "Não"}</dd></div>
      <div><dt>ID</dt><dd>${data.person_id || "-"}</dd></div>
      <div><dt>Nome</dt><dd>${data.name || "-"}</dd></div>
      <div><dt>ID Unidade</dt><dd>${data.unit_id || "-"}</dd></div>
      <div><dt>Unidade</dt><dd>${data.unit || "-"}</dd></div>
      <div><dt>Função</dt><dd>${data.role || "-"}</dd></div>
      <div><dt>Confiança</dt><dd>${formatConfidence(data.confidence)}</dd></div>
    </dl>
  `;
}

function unitOptions(selectedValue = "", placeholder = "Selecione uma unidade") {
  const selected = selectedValue === null || selectedValue === undefined ? "" : String(selectedValue);
  const options = state.units.map((unit) => (
    `<option value="${unit.id}" ${String(unit.id) === selected ? "selected" : ""}>${unit.id} - ${unit.name}</option>`
  )).join("");

  return `<option value="">${placeholder}</option>${options}`;
}

function renderUnits() {
  $("#personUnitSelect").innerHTML = unitOptions("", "Selecione uma unidade");
  $("#manualUnitSelect").innerHTML = unitOptions("", "Selecione uma unidade");
}

function renderPeople() {
  const rows = $("#peopleRows");
  const photoSelect = $("#photoPersonSelect");

  rows.innerHTML = state.people.length
    ? state.people.map((person) => `
        <tr>
          <td>
            <div class="table-actions">
              <button class="secondary action-button" type="button" data-person-edit="${person.person_id}">
                Editar
              </button>
              <button class="danger-button" type="button" data-person-delete="${person.person_id}">
                Remover
              </button>
            </div>
          </td>
          <td>${person.person_id}</td>
          <td>${person.name}</td>
          <td>${person.unit || "-"}</td>
          <td>${person.role || "-"}</td>
          <td><span class="badge">${person.photos_count || 0}</span></td>
        </tr>
      `).join("")
    : emptyRow(6, "Nenhuma pessoa cadastrada.");

  const options = state.people.map((person) => (
    `<option value="${person.person_id}">${person.person_id} - ${person.name}</option>`
  )).join("");
  photoSelect.innerHTML = options || '<option value="">Cadastre uma pessoa primeiro</option>';
  renderManualOptions();
}

function resetPersonForm() {
  const form = $("#personForm");
  form.reset();
  form.dataset.mode = "create";
  delete form.dataset.editingPersonId;
  state.editingPersonId = null;
  const idInput = form.elements.person_id;
  idInput.disabled = false;
  $("#personSubmitButton").textContent = "Cadastrar pessoa";
  $("#personCancelButton").hidden = true;
  if (state.units.length) {
    $("#personUnitSelect").innerHTML = unitOptions("", "Selecione uma unidade");
  }
}

function startPersonEdit(personId) {
  const person = state.people.find((item) => item.person_id === personId);
  if (!person) return;

  const form = $("#personForm");
  form.dataset.mode = "edit";
  form.dataset.editingPersonId = person.person_id;
  state.editingPersonId = person.person_id;
  form.elements.person_id.value = person.person_id;
  form.elements.person_id.disabled = true;
  form.elements.name.value = person.name || "";
  $("#personUnitSelect").innerHTML = unitOptions(person.unit_id ?? "", "Selecione uma unidade");
  form.elements.role.value = person.role || "";
  $("#personSubmitButton").textContent = "Salvar alterações";
  $("#personCancelButton").hidden = false;
  setPage("people");
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
          <td>${item.unit || "-"}</td>
          <td><span class="badge ${item.method === "face" ? "ok" : ""}">${item.method}</span></td>
          <td>${formatConfidence(item.confidence)}</td>
          <td>${item.already_checked_in ? "Sim" : "Não"}</td>
          <td>${formatDate(item.checked_in_at)}</td>
        </tr>
      `).join("")
    : emptyRow(8, "Nenhum credenciamento registrado.");
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
        <article><strong>${item.name}</strong><span>${item.unit || "-"} - ${item.method} - ${formatDate(item.checked_in_at)}</span></article>
      `).join("")
    : '<p class="empty-text">Sem credenciamentos.</p>';

  $("#latestLogs").innerHTML = (data.latest_logs || []).length
    ? data.latest_logs.map((item) => `
        <article><strong>${item.action}</strong><span>${item.message || "-"}</span></article>
      `).join("")
    : '<p class="empty-text">Sem logs.</p>';
}

function renderFormsImportResult(response) {
  const summary = response.summary || {};
  const errors = response.errors || [];
  const result = $("#formsImportResult");
  const errorRows = errors.length
    ? errors.map((error) => `
        <tr>
          <td>${error.row || "-"}</td>
          <td>${error.person_id || "-"}</td>
          <td>${error.name || "-"}</td>
          <td><span class="badge danger">${error.code || "-"}</span></td>
          <td>${error.message || "-"}</td>
          <td>${error.expected_filename || "-"}</td>
        </tr>
      `).join("")
    : emptyRow(6, "Nenhum erro encontrado.");

  result.className = "import-result";
  result.innerHTML = `
    <div class="metrics import-metrics">
      <article class="metric"><span>Linhas</span><strong>${summary.total_rows || 0}</strong></article>
      <article class="metric"><span>Importados</span><strong>${summary.imported || 0}</strong></article>
      <article class="metric"><span>Fotos completadas</span><strong>${summary.photo_completed || 0}</strong></article>
      <article class="metric"><span>Ignorados</span><strong>${summary.ignored || 0}</strong></article>
      <article class="metric"><span>Erros</span><strong>${summary.errors_count || 0}</strong></article>
    </div>
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Linha</th>
            <th>ID</th>
            <th>Nome</th>
            <th>Código</th>
            <th>Mensagem</th>
            <th>Foto esperada</th>
          </tr>
        </thead>
        <tbody>${errorRows}</tbody>
      </table>
    </div>
  `;
}

async function loadUnits() {
  const data = await requestJson("/units");
  state.units = data.units || [];
  renderUnits();
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
    await loadUnits();
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
  const mode = form.dataset.mode || "create";
  const payload = new FormData(form);
  const personId = mode === "edit" ? form.dataset.editingPersonId : payload.get("person_id");
  try {
    const data = await requestJson(
      mode === "edit" ? `/people/${encodeURIComponent(personId)}` : "/people",
      { method: mode === "edit" ? "PUT" : "POST", body: payload },
    );
    resetPersonForm();
    toast(data.message || (mode === "edit" ? "Pessoa atualizada com sucesso." : "Pessoa cadastrada com sucesso."));
    await refreshAll();
  } catch (error) {
    toast(error.message, "error");
  }
});

$("#personCancelButton").addEventListener("click", resetPersonForm);

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

$("#formsImportForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const button = form.querySelector('button[type="submit"]');
  const resultElement = $("#formsImportResult");

  button.disabled = true;
  button.textContent = "Importando...";
  resultElement.className = "empty-text";
  resultElement.textContent = "Processando planilha e fotos...";

  try {
    const response = await requestJson("/api/imports/forms", {
      method: "POST",
      body: new FormData(form),
    });
    renderFormsImportResult(response);
    const errorsCount = response.summary?.errors_count || 0;
    toast(errorsCount ? `Importação concluída com ${errorsCount} erro(s).` : "Importação concluída com sucesso.", errorsCount ? "warn" : "success");
    form.reset();
    await refreshAll();
  } catch (error) {
    resultElement.textContent = error.message;
    toast(error.message, "error");
  } finally {
    button.disabled = false;
    button.textContent = "Importar participantes";
  }
});

$("#recognizeForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const image = selectedCapture("recognize");

  if (!image) {
    toast("Selecione uma imagem ou tire uma foto para o check-in facial.", "error");
    return;
  }

  const payload = new FormData(form);
  payload.delete("image");
  payload.append("image", image, "checkin-facial.jpg");
  payload.append("source", "web_frontend");
  payload.append("robot_id", "web-admin");

  try {
    const data = await requestJson("/checkin-face", { method: "POST", body: payload });
    renderRecognitionResult(data);
    toast(data.message || "Check-in facial concluído.", data.recognized ? "success" : "warn");
    await refreshAll();
  } catch (error) {
    toast(error.message, "error");
  }
});

$("#manualSearch").addEventListener("input", renderManualOptions);

$("#peopleRows").addEventListener("click", async (event) => {
  const editButton = event.target.closest("[data-person-edit]");
  if (editButton) {
    startPersonEdit(editButton.dataset.personEdit);
    return;
  }

  const deleteButton = event.target.closest("[data-person-delete]");
  if (!deleteButton) return;

  const personId = deleteButton.dataset.personDelete;
  const person = state.people.find((item) => item.person_id === personId);
  const label = person ? `${person.name} (${person.person_id})` : personId;

  if (!window.confirm(`Remover a pessoa ${label} e todos os dados dela?`)) return;

  deleteButton.disabled = true;
  try {
    const data = await requestJson(`/people/${encodeURIComponent(personId)}`, { method: "DELETE" });
    if (state.editingPersonId === personId) {
      resetPersonForm();
    }
    toast(data.message || "Pessoa removida com sucesso.");
    await refreshAll();
  } catch (error) {
    deleteButton.disabled = false;
    toast(error.message, "error");
  }
});

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
