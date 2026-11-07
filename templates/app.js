(() => {
  const form = document.querySelector("#upload-form");
  const input = document.querySelector("#file-input");
  const dropZone = document.querySelector("#drop-zone");
  const selectedFiles = document.querySelector("#selected-files");
  const uploadButton = document.querySelector("#upload-button");
  const results = document.querySelector("#upload-results");
  const keyMeta = document.querySelector('meta[name="docinbox-key"]');
  const accessKey = keyMeta ? keyMeta.content : "";

  if (!form || !input || !dropZone || !selectedFiles || !uploadButton || !results) {
    return;
  }

  let filesToUpload = [];

  const formatBytes = (bytes) => {
    if (bytes < 1024) return bytes + " B";
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
    return (bytes / (1024 * 1024)).toFixed(1) + " MB";
  };

  const setFiles = (files) => {
    filesToUpload = Array.from(files || []);
    selectedFiles.replaceChildren();
    uploadButton.disabled = filesToUpload.length === 0;
    if (filesToUpload.length === 0) return;

    const heading = document.createElement("p");
    heading.className = "selected-heading";
    heading.textContent = filesToUpload.length + " archivo(s) seleccionado(s)";
    selectedFiles.append(heading);

    const list = document.createElement("ul");
    for (const file of filesToUpload) {
      const item = document.createElement("li");
      const name = document.createElement("span");
      const size = document.createElement("small");
      name.textContent = file.name;
      size.textContent = formatBytes(file.size);
      item.append(name, size);
      list.append(item);
    }
    selectedFiles.append(list);
  };

  input.addEventListener("change", () => setFiles(input.files));

  ["dragenter", "dragover"].forEach((eventName) => {
    dropZone.addEventListener(eventName, (event) => {
      event.preventDefault();
      dropZone.classList.add("is-dragging");
    });
  });

  ["dragleave", "drop"].forEach((eventName) => {
    dropZone.addEventListener(eventName, (event) => {
      event.preventDefault();
      dropZone.classList.remove("is-dragging");
    });
  });

  dropZone.addEventListener("drop", (event) => {
    const droppedFiles = event.dataTransfer && event.dataTransfer.files;
    if (droppedFiles && droppedFiles.length) setFiles(droppedFiles);
  });

  const addResult = (filename, message, status) => {
    const item = document.createElement("div");
    item.className = "result-item " + status;
    const name = document.createElement("strong");
    const detail = document.createElement("span");
    name.textContent = filename;
    detail.textContent = message;
    item.append(name, detail);
    results.prepend(item);
  };

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (filesToUpload.length === 0 || uploadButton.disabled) return;

    uploadButton.disabled = true;
    uploadButton.textContent = "Enviando…";
    results.replaceChildren();

    let succeeded = 0;
    for (const file of filesToUpload) {
      const body = new FormData();
      body.append("file", file, file.name);
      try {
        const headers = accessKey ? { "X-DocInBox-Key": accessKey } : {};
        const response = await fetch("/api/upload", {
          method: "POST",
          headers,
          body
        });
        const payload = await response.json();
        if (!response.ok) throw new Error(payload.error || "No fue posible enviar el archivo.");
        succeeded += 1;
        addResult(file.name, "Recibido · " + formatBytes(payload.size), "success");
      } catch (error) {
        addResult(file.name, error.message || "Error de conexión.", "error");
      }
    }

    const total = filesToUpload.length;
    uploadButton.textContent = succeeded + " de " + total + " enviados";
    input.value = "";
    filesToUpload = [];
    selectedFiles.replaceChildren();

    window.setTimeout(() => {
      uploadButton.textContent = "Enviar documentos";
      uploadButton.disabled = true;
    }, 2500);
  });
})();
