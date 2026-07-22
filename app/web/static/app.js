const searchInput = document.querySelector("#document-search");
const documentsMessage = document.querySelector("#documents-message");
const tableContainer = document.querySelector("#documents-table-container");
const documentForm = document.querySelector("#document-form");
const formMessage = document.querySelector("#form-message");
const submitButton = document.querySelector("#submit-document");
const workItems = document.querySelector("#work-items");
const customerSelect = document.querySelector("#customer-id");
const objectSelect = document.querySelector("#object-id");

let searchTimer;
let customers = [];
let projectObjects = [];

const statusLabels = { pending: "Ожидает генерации", generated: "Сформирован", error: "Ошибка" };

function escapeHtml(value) {
  const element = document.createElement("span");
  element.textContent = String(value);
  return element.innerHTML;
}

function formatDate(value) {
  const date = new Date(`${value.replace(" ", "T")}Z`);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString("ru-RU");
}

function showView() {
  const view = window.location.hash === "#create" ? "create" : "list";
  document.querySelectorAll("[data-view]").forEach((element) => { element.hidden = element.dataset.view !== view; });
  document.querySelectorAll("[data-view-link]").forEach((element) => {
    const active = element.dataset.viewLink === view;
    element.classList.toggle("navigation__link--active", active);
    element.toggleAttribute("aria-current", active);
  });
  if (view === "list") loadDocuments();
  if (view === "create") loadReferences();
}

function renderDocuments(documents) {
  if (!documents.length) {
    tableContainer.innerHTML = "";
    documentsMessage.textContent = "Ничего не найдено";
    return;
  }
  documentsMessage.textContent = "";
  tableContainer.innerHTML = `<table class="documents-table"><thead><tr><th>№</th><th>Заказчик</th><th>Объект</th><th>Тема</th><th>Создан</th><th>Статус</th></tr></thead><tbody>${documents.map((document) => `<tr><td data-label="№">${document.id}</td><td data-label="Заказчик">${escapeHtml(document.customer_name)}</td><td data-label="Объект">${escapeHtml(document.object_name)}</td><td data-label="Тема">${escapeHtml(document.subject)}</td><td data-label="Создан">${escapeHtml(formatDate(document.created_at))}</td><td data-label="Статус"><span class="status status--${escapeHtml(document.status)}">${statusLabels[document.status] || escapeHtml(document.status)}</span></td></tr>`).join("")}</tbody></table>`;
}

async function loadDocuments() {
  const search = searchInput.value.trim();
  documentsMessage.className = "message";
  documentsMessage.textContent = "Загрузка списка…";
  tableContainer.innerHTML = "";
  try {
    const response = await fetch(`/api/documents?search=${encodeURIComponent(search)}`);
    if (!response.ok) throw new Error();
    renderDocuments(await response.json());
  } catch {
    documentsMessage.className = "message message--error";
    documentsMessage.textContent = "Не удалось загрузить список. Попробуйте обновить страницу.";
  }
}

function renderReferenceOptions(select, items) {
  select.innerHTML = `<option value="">${select.options[0].text}</option>${items.map((item) => `<option value="${item.id}">${escapeHtml(item.name)}</option>`).join("")}`;
}

async function loadReferences() {
  if (customers.length && projectObjects.length) return;
  try {
    const [customersResponse, objectsResponse] = await Promise.all([fetch("/api/customers"), fetch("/api/project-objects")]);
    if (!customersResponse.ok || !objectsResponse.ok) throw new Error();
    customers = await customersResponse.json();
    projectObjects = await objectsResponse.json();
    renderReferenceOptions(customerSelect, customers);
    renderReferenceOptions(objectSelect, projectObjects);
  } catch {
    formMessage.className = "message message--error";
    formMessage.textContent = "Не удалось загрузить справочники. Попробуйте обновить страницу.";
  }
}

function setReferenceFields(select, items, fields) {
  const item = items.find((entry) => String(entry.id) === select.value);
  fields.forEach(([id, key]) => { document.querySelector(id).value = item ? item[key] : ""; });
}

function addWorkItem() {
  const row = document.createElement("div");
  row.className = "work-item";
  row.innerHTML = `<label class="form-field">Наименование<input class="work-item-name" type="text" required></label><label class="form-field">Комментарий<input class="work-item-comment" type="text"></label><button class="remove-work-item" type="button" aria-label="Удалить строку">Удалить</button>`;
  row.querySelector(".remove-work-item").addEventListener("click", () => { if (workItems.children.length > 1) row.remove(); });
  workItems.append(row);
}

function clearFieldErrors() {
  document.querySelectorAll(".field-error").forEach((element) => { element.textContent = ""; });
}

function showFieldErrors(errors) {
  Object.entries(errors).forEach(([field, text]) => {
    const error = document.querySelector(`[data-error-for="${field}"]`);
    if (error) error.textContent = text;
  });
}

document.querySelector("#add-work-item").addEventListener("click", addWorkItem);
customerSelect.addEventListener("change", () => setReferenceFields(customerSelect, customers, [["#customer-director", "director"]]));
objectSelect.addEventListener("change", () => setReferenceFields(objectSelect, projectObjects, [["#object-imo", "imo"]]));

searchInput.addEventListener("input", () => { clearTimeout(searchTimer); searchTimer = setTimeout(loadDocuments, 300); });
searchInput.addEventListener("keydown", (event) => { if (event.key === "Enter") { clearTimeout(searchTimer); loadDocuments(); } });

documentForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  clearFieldErrors();
  formMessage.className = "message";
  if (!documentForm.checkValidity()) { documentForm.reportValidity(); return; }
  const formData = new FormData(documentForm);
  const payload = Object.fromEntries(formData.entries());
  payload.work_items = [...workItems.children].map((row) => ({ name: row.querySelector(".work-item-name").value, comment: row.querySelector(".work-item-comment").value }));
  submitButton.disabled = true;
  submitButton.textContent = "Создание…";
  try {
    const response = await fetch("/api/documents", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
    const result = await response.json();
    if (!response.ok) {
      showFieldErrors(result.detail?.errors || {});
      formMessage.className = "message message--error";
      formMessage.textContent = "Проверьте заполнение формы.";
      return;
    }

    const generationResponse = await fetch(`/api/documents/${result.id}/generate`, { method: "POST" });
    if (!generationResponse.ok) {
      formMessage.className = "message message--error";
      formMessage.textContent = `Запись документа №${result.id} создана, но Word-файл сформировать не удалось.`;
      return;
    }
    formMessage.className = "message message--success";
    formMessage.textContent = `Документ №${result.id} создан и Word-файл сформирован.`;
    documentForm.reset();
    document.querySelector("#customer-director").value = "";
    document.querySelector("#object-imo").value = "";
    workItems.replaceChildren();
    addWorkItem();
  } catch {
    formMessage.className = "message message--error";
    formMessage.textContent = "Не удалось создать документ. Попробуйте ещё раз.";
  } finally {
    submitButton.disabled = false;
    submitButton.textContent = "Создать документ";
  }
});

window.addEventListener("hashchange", showView);
addWorkItem();
showView();
