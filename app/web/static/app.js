const searchInput = document.querySelector("#document-search");
const documentsMessage = document.querySelector("#documents-message");
const tableContainer = document.querySelector("#documents-table-container");
const documentForm = document.querySelector("#document-form");
const formMessage = document.querySelector("#form-message");
const submitButton = document.querySelector("#submit-document");
const workItems = document.querySelector("#work-items");
const customerSelect = document.querySelector("#customer-id");
const objectSelect = document.querySelector("#object-id");
const commandForm = document.querySelector("#command-form");
const commandInput = document.querySelector("#command-input");
const chatHistory = document.querySelector("#chat-history");
const voiceCommandButton = document.querySelector("#voice-command-button");
const voiceResponseToggle = document.querySelector("#voice-response-toggle");
const helpButton = document.querySelector("#help-button");
const helpDialog = document.querySelector("#help-dialog");
const helpCommands = document.querySelector("#help-commands");

let searchTimer;
let customers = [];
let projectObjects = [];
let isListening = false;
let isVoiceResponseEnabled = false;
let commandAliases = [];
let commandAliasesPromise;
let commandAliasesLoaded = false;
let commandAliasesLoadError = false;

const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
const speechRecognition = SpeechRecognition ? new SpeechRecognition() : null;
const speechSynthesisSupported = "speechSynthesis" in window;

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

function addChatMessage(text, role, shouldSpeak = false) {
  const message = document.createElement("div");
  message.className = `chat-message chat-message--${role}`;
  const paragraph = document.createElement("p");
  paragraph.textContent = text;
  message.append(paragraph);
  chatHistory.append(message);
  message.scrollIntoView({ block: "nearest" });
  if (shouldSpeak) speakResponse(text);
}

function addChatLinkMessage(text, url, linkLabel) {
  const message = document.createElement("div");
  message.className = "chat-message chat-message--agent";
  const paragraph = document.createElement("p");
  paragraph.textContent = text;
  const link = document.createElement("a");
  link.href = url;
  link.target = "_blank";
  link.rel = "noopener noreferrer";
  link.textContent = linkLabel;
  message.append(paragraph, link);
  chatHistory.append(message);
  message.scrollIntoView({ block: "nearest" });
}

function speakResponse(text) {
  if (!isVoiceResponseEnabled || !speechSynthesisSupported) return;
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = "ru-RU";
  window.speechSynthesis.speak(utterance);
}

function setVoiceResponseState(enabled) {
  isVoiceResponseEnabled = enabled && speechSynthesisSupported;
  voiceResponseToggle.setAttribute("aria-pressed", String(isVoiceResponseEnabled));
  const label = isVoiceResponseEnabled ? "Озвучка: включена" : "Озвучка: выключена";
  voiceResponseToggle.textContent = isVoiceResponseEnabled ? "🔊" : "🔇";
  voiceResponseToggle.setAttribute("aria-label", label);
  voiceResponseToggle.title = label;
}

function submitCommand(command) {
  const normalizedCommand = command.trim();
  if (!normalizedCommand) return;
  addChatMessage(normalizedCommand, "user");
  commandInput.value = "";
  if (!commandAliasesLoaded) {
    const message = commandAliasesLoadError
      ? "Не удалось загрузить команды ассистента. Попробуйте обновить страницу."
      : "Команды ассистента загружаются. Повторите команду через секунду.";
    addChatMessage(message, "agent", true);
    return;
  }
  const commandAlias = getCommandAlias(normalizedCommand);
  const searchCommand = getSearchCommand(normalizedCommand);
  if (searchCommand) {
    openSearch(searchCommand);
    return;
  }
  if (commandAlias?.action_code === "create_document") {
    addChatMessage("Открываю форму создания коммерческого предложения.", "agent", true);
    window.location.hash = "#create";
    showView();
    return;
  }
  if (commandAlias?.action_code === "open_mail") {
    openMail(commandAlias);
    return;
  }
  if (commandAlias?.action_code === "open_site") {
    openWebsite(commandAlias);
    return;
  }
  addChatMessage("Пока я умею создавать КП. Скажите «Создай КП».", "agent", true);
}

function normalizeCommand(command) {
  return command
    .trim()
    .toLocaleLowerCase("ru-RU")
    .replace(/[!?.;,:«»„“]/g, "")
    .replace(/\s+/g, "");
}

function getCommandAlias(command) {
  const normalizedPhrase = normalizeCommand(command);
  return commandAliases.find((alias) => alias.normalized_phrase === normalizedPhrase);
}

function getSearchCommand(command) {
  const sourceCommand = command.trim();
  const normalizedCommand = sourceCommand.toLocaleLowerCase("ru-RU");
  const searchAlias = commandAliases
    .filter((alias) => alias.action_code === "web_search" && alias.requires_query)
    .sort((first, second) => second.phrase.length - first.phrase.length)
    .find((alias) => {
      const prefix = alias.phrase.toLocaleLowerCase("ru-RU");
      return normalizedCommand === prefix || normalizedCommand.startsWith(`${prefix} `) || normalizedCommand.startsWith(`${prefix},`);
    });
  if (!searchAlias) return null;

  const query = sourceCommand
    .slice(searchAlias.phrase.length)
    .replace(/^[\s,.:;!?—-]+/, "")
    .trim();
  return { alias: searchAlias, query };
}

function loadCommandAliases() {
  if (commandAliasesPromise) return commandAliasesPromise;
  commandAliasesPromise = fetch("/api/assistant/commands")
    .then((response) => {
      if (!response.ok) throw new Error("Commands are unavailable");
      return response.json();
    })
    .then((commands) => {
      commandAliases = commands.filter((command) => ["create_document", "open_mail", "web_search", "open_site"].includes(command.action_code));
      commandAliasesLoaded = true;
    })
    .catch((error) => {
      commandAliasesLoadError = true;
      throw error;
    });
  return commandAliasesPromise;
}

function openMail(commandAlias) {
  const targetUrl = getSecureMailUrl(commandAlias);
  if (!targetUrl) {
    addChatMessage("Почтовый ящик сейчас недоступен.", "agent", true);
    return;
  }
  addChatMessage("Открываю почтовый ящик.", "agent", true);
  window.open(targetUrl, "_blank", "noopener,noreferrer");
  addChatLinkMessage("Если браузер заблокировал новую вкладку, используйте ссылку:", targetUrl, "Открыть почту");
}

function getSecureMailUrl(commandAlias) {
  if (commandAlias.action_code !== "open_mail" || !commandAlias.target_url) return null;
  try {
    const url = new URL(commandAlias.target_url);
    return url.protocol === "https:" ? url.href : null;
  } catch {
    return null;
  }
}

function openWebsite(commandAlias) {
  const targetUrl = getSecureWebsiteUrl(commandAlias);
  if (!targetUrl) {
    addChatMessage("Сайт сейчас недоступен.", "agent", true);
    return;
  }
  const websiteName = commandAlias.website_name || "сайт";
  addChatMessage(`Открываю: ${websiteName}.`, "agent", true);
  window.open(targetUrl, "_blank", "noopener,noreferrer");
  addChatLinkMessage(
    "Если браузер заблокировал новую вкладку, используйте ссылку:",
    targetUrl,
    `Открыть ${websiteName}`
  );
}

function getSecureWebsiteUrl(commandAlias) {
  if (commandAlias.action_code !== "open_site" || !commandAlias.website_name || !commandAlias.target_url) return null;
  try {
    const url = new URL(commandAlias.target_url);
    return url.protocol === "https:" ? url.href : null;
  } catch {
    return null;
  }
}

function openSearch(searchCommand) {
  if (!searchCommand.query) {
    addChatMessage("Что найти? Например: «Найди правила классификации судов».", "agent", true);
    return;
  }
  const targetUrl = getSecureSearchUrl(searchCommand.alias, searchCommand.query);
  if (!targetUrl) {
    addChatMessage("Поиск сейчас недоступен.", "agent", true);
    return;
  }
  addChatMessage(`Ищу: ${searchCommand.query}`, "agent", true);
  window.open(targetUrl, "_blank", "noopener,noreferrer");
  addChatLinkMessage("Если браузер заблокировал новую вкладку, используйте ссылку:", targetUrl, "Открыть поиск");
}

function getSecureSearchUrl(commandAlias, query) {
  if (commandAlias.action_code !== "web_search" || !commandAlias.requires_query || !commandAlias.target_url) return null;
  try {
    const url = new URL(commandAlias.target_url);
    return url.protocol === "https:" ? `${url.href}${encodeURIComponent(query)}` : null;
  } catch {
    return null;
  }
}

function renderHelpCommands() {
  helpCommands.replaceChildren();
  if (!commandAliases.length) {
    const item = document.createElement("li");
    item.textContent = "Доступные команды пока не загружены.";
    helpCommands.append(item);
    return;
  }
  commandAliases.forEach((command) => {
    const item = document.createElement("li");
    item.textContent = command.phrase;
    helpCommands.append(item);
  });
}

function openHelp() {
  helpDialog.showModal();
  loadCommandAliases()
    .then(renderHelpCommands)
    .catch(() => {
      helpCommands.replaceChildren();
      const item = document.createElement("li");
      item.textContent = "Не удалось загрузить доступные команды.";
      helpCommands.append(item);
    });
}

function setListeningState(listening) {
  isListening = listening;
  voiceCommandButton.classList.toggle("button--listening", listening);
  voiceCommandButton.setAttribute("aria-pressed", String(listening));
  voiceCommandButton.setAttribute(
    "aria-label",
    listening ? "Остановить голосовой ввод" : "Начать голосовой ввод"
  );
  voiceCommandButton.textContent = listening ? "■" : "🎙";
}

function speechErrorMessage(error) {
  if (error === "not-allowed" || error === "service-not-allowed") {
    return "Доступ к микрофону запрещён. Разрешите его в настройках браузера.";
  }
  if (error === "no-speech") {
    return "Речь не распознана. Попробуйте сказать команду ещё раз.";
  }
  return "Голосовой ввод сейчас недоступен. Используйте текстовую команду.";
}

if (speechRecognition) {
  speechRecognition.lang = "ru-RU";
  speechRecognition.interimResults = false;
  speechRecognition.continuous = false;
  speechRecognition.onstart = () => setListeningState(true);
  speechRecognition.onresult = (event) => {
    submitCommand(event.results[0][0].transcript);
  };
  speechRecognition.onerror = (event) => addChatMessage(speechErrorMessage(event.error), "agent");
  speechRecognition.onend = () => setListeningState(false);
}

function showView() {
  const hashView = window.location.hash.slice(1);
  const view = ["assistant", "list", "create"].includes(hashView) ? hashView : "assistant";
  document.querySelectorAll("[data-view]").forEach((element) => { element.hidden = element.dataset.view !== view; });
  document.querySelectorAll("[data-view-link]").forEach((element) => {
    const active = element.dataset.viewLink === view;
    element.classList.toggle("navigation__link--active", active);
    element.toggleAttribute("aria-current", active);
  });
  if (view === "list") loadDocuments();
  if (view === "create") loadReferences();
  if (view === "assistant") loadCommandAliases().catch(() => {});
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

commandForm.addEventListener("submit", (event) => {
  event.preventDefault();
  submitCommand(commandInput.value);
});

voiceCommandButton.addEventListener("click", () => {
  if (!speechRecognition) {
    addChatMessage("Этот браузер не поддерживает голосовой ввод. Используйте текстовую команду.", "agent");
    return;
  }
  if (isListening) {
    speechRecognition.stop();
    return;
  }
  try {
    speechRecognition.start();
  } catch {
    addChatMessage("Не удалось запустить голосовой ввод. Используйте текстовую команду.", "agent");
  }
});

voiceResponseToggle.addEventListener("click", () => {
  setVoiceResponseState(!isVoiceResponseEnabled);
  if (!speechSynthesisSupported) {
    addChatMessage("Этот браузер не поддерживает голосовую озвучку.", "agent");
  }
});

helpButton.addEventListener("click", openHelp);
document.querySelectorAll("[data-close-help]").forEach((button) => {
  button.addEventListener("click", () => helpDialog.close());
});
helpDialog.addEventListener("click", (event) => {
  if (event.target === helpDialog) helpDialog.close();
});

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
setVoiceResponseState(true);
showView();
