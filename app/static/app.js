const state = {
  enroll: { stream: null, imageBlob: null, source: "camera" },
  recognize: { stream: null, imageBlob: null, source: "camera" },
};

const elements = {
  result: document.querySelector("#result"),
  tabs: document.querySelectorAll(".tab"),
  flows: document.querySelectorAll(".flow"),
};

function modeElements(mode) {
  return {
    block: document.querySelector(`.capture-block[data-mode="${mode}"]`),
    video: document.querySelector(`#${mode}Video`),
    canvas: document.querySelector(`#${mode}Canvas`),
    upload: document.querySelector(`#${mode}Upload`),
    preview: document.querySelector(`#${mode}Preview`),
  };
}

function showResult(title, data, type = "success") {
  elements.result.hidden = false;
  elements.result.className = `result ${type}`;

  const lines = Object.entries(data || {})
    .map(([key, value]) => `<p><strong>${key}:</strong> ${String(value)}</p>`)
    .join("");

  elements.result.innerHTML = `<h2>${title}</h2>${lines}`;
}

function showError(error) {
  const detail = error?.detail || error?.message || "Erro inesperado";
  showResult("Erro", { detalhe: detail }, "error");
}

function setBusy(form, busy) {
  form.querySelectorAll("button").forEach((button) => {
    button.disabled = busy;
  });
}

async function startCamera(mode) {
  const current = state[mode];
  const { video } = modeElements(mode);

  if (current.stream) {
    current.stream.getTracks().forEach((track) => track.stop());
  }

  current.stream = await navigator.mediaDevices.getUserMedia({
    video: { facingMode: "user" },
    audio: false,
  });

  video.srcObject = current.stream;
}

function capturePhoto(mode) {
  const current = state[mode];
  const { video, canvas, preview } = modeElements(mode);

  if (!video.srcObject || video.videoWidth === 0) {
    throw new Error("Abra a câmera antes de tirar a foto.");
  }

  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;
  canvas.getContext("2d").drawImage(video, 0, 0, canvas.width, canvas.height);

  canvas.toBlob((blob) => {
    current.imageBlob = blob;
    preview.src = URL.createObjectURL(blob);
    preview.hidden = false;
  }, "image/jpeg", 0.92);
}

function setSource(mode, source) {
  const current = state[mode];
  const { block, upload, preview } = modeElements(mode);

  current.source = source;
  current.imageBlob = null;
  upload.value = "";
  preview.hidden = true;
  preview.removeAttribute("src");

  block.querySelectorAll(".mode-button").forEach((button) => {
    button.classList.toggle("is-active", button.dataset.source === source);
  });

  block.querySelectorAll("[data-source-panel]").forEach((panel) => {
    panel.classList.toggle("is-active", panel.dataset.sourcePanel === source);
  });
}

function selectedImage(mode) {
  const current = state[mode];
  const { upload } = modeElements(mode);

  if (current.source === "upload") {
    return upload.files[0] || null;
  }

  return current.imageBlob;
}

async function postForm(url, formData) {
  const response = await fetch(url, {
    method: "POST",
    body: formData,
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw data;
  }

  return data;
}

elements.tabs.forEach((tab) => {
  tab.addEventListener("click", () => {
    elements.tabs.forEach((item) => item.classList.toggle("is-active", item === tab));
    elements.flows.forEach((flow) => {
      flow.classList.toggle("is-active", flow.dataset.flow === tab.dataset.tab);
    });
  });
});

document.querySelectorAll(".capture-block").forEach((block) => {
  const mode = block.dataset.mode;

  block.querySelectorAll(".mode-button").forEach((button) => {
    button.addEventListener("click", () => setSource(mode, button.dataset.source));
  });

  block.querySelector('[data-action="start-camera"]').addEventListener("click", async () => {
    try {
      await startCamera(mode);
    } catch (error) {
      showError(error);
    }
  });

  block.querySelector('[data-action="capture"]').addEventListener("click", () => {
    try {
      capturePhoto(mode);
    } catch (error) {
      showError(error);
    }
  });

  modeElements(mode).upload.addEventListener("change", (event) => {
    const file = event.target.files[0];
    const { preview } = modeElements(mode);

    state[mode].imageBlob = null;

    if (!file) {
      preview.hidden = true;
      preview.removeAttribute("src");
      return;
    }

    preview.src = URL.createObjectURL(file);
    preview.hidden = false;
  });
});

document.querySelector("#enrollForm").addEventListener("submit", async (event) => {
  event.preventDefault();

  const form = event.currentTarget;
  const image = selectedImage("enroll");

  if (!image) {
    showError(new Error("Selecione uma imagem ou tire uma foto para cadastrar."));
    return;
  }

  const formData = new FormData();
  formData.append("person_id", document.querySelector("#personId").value.trim());
  formData.append("name", document.querySelector("#personName").value.trim());
  formData.append("image", image, "cadastro.jpg");

  try {
    setBusy(form, true);
    const data = await postForm("/enroll", formData);
    showResult("Cadastro concluído", data);
  } catch (error) {
    showError(error);
  } finally {
    setBusy(form, false);
  }
});

document.querySelector("#recognizeForm").addEventListener("submit", async (event) => {
  event.preventDefault();

  const form = event.currentTarget;
  const image = selectedImage("recognize");

  if (!image) {
    showError(new Error("Selecione uma imagem ou tire uma foto para reconhecer."));
    return;
  }

  const formData = new FormData();
  formData.append("image", image, "reconhecimento.jpg");

  try {
    setBusy(form, true);
    const data = await postForm("/recognize", formData);
    showResult("Resultado do reconhecimento", data, data.recognized ? "success" : "error");
  } catch (error) {
    showError(error);
  } finally {
    setBusy(form, false);
  }
});
