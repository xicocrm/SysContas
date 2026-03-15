const statusEl = document.getElementById("status");
const outputEl = document.getElementById("output");
const setupCard = document.getElementById("setupCard");
const appWorkspace = document.getElementById("appWorkspace");
const authShell = document.getElementById("authShell");
const moduleButtons = document.querySelectorAll(".module-btn");
const moduleSections = document.querySelectorAll(".module-section");

function byId(id) {
  return document.getElementById(id);
}

function onClick(id, handler) {
  const element = byId(id);
  if (element) {
    element.addEventListener("click", handler);
  }
}

function setStatus(message, ok = true) {
  if (statusEl) {
    statusEl.innerHTML = `<div class="status ${ok ? "ok" : "err"}">${message}</div>`;
  }
}

function showOutput(data) {
  if (outputEl) {
    outputEl.textContent = JSON.stringify(data, null, 2);
  }
}

function getToken() {
  return localStorage.getItem("sysconta_token");
}

function setToken(token) {
  localStorage.setItem("sysconta_token", token);
}

function clearToken() {
  localStorage.removeItem("sysconta_token");
}

function activateModule(moduleName) {
  moduleSections.forEach((section) => section.classList.add("hidden"));
  moduleButtons.forEach((btn) => btn.classList.remove("active"));

  const target = byId(`module-${moduleName}`);
  if (target) {
    target.classList.remove("hidden");
  }
  const activeBtn = document.querySelector(`.module-btn[data-module="${moduleName}"]`);
  if (activeBtn) {
    activeBtn.classList.add("active");
  }
}

function refreshAuthUI() {
  const hasToken = !!getToken();
  if (appWorkspace) appWorkspace.classList.toggle("hidden", !hasToken);
  if (authShell) authShell.classList.toggle("hidden", hasToken);
  if (hasToken) {
    activateModule("cadastros");
  }
}

async function request(path, { method = "GET", body, auth = false, form = false } = {}) {
  const headers = {};
  if (auth && getToken()) {
    headers.Authorization = `Bearer ${getToken()}`;
  }
  if (!form) {
    headers["Content-Type"] = "application/json";
  }

  const res = await fetch(path, {
    method,
    headers,
    body: form ? body : body ? JSON.stringify(body) : undefined,
  });

  const text = await res.text();
  let data;
  try {
    data = text ? JSON.parse(text) : {};
  } catch {
    data = { raw: text };
  }
  if (!res.ok) {
    throw new Error(data.detail || data.message || `Erro ${res.status}`);
  }
  return data;
}

onClick("btnCriarEmpresa", async () => {
  try {
    const payload = {
      nome: byId("empresaNome").value,
      cnpj: byId("empresaCnpj").value || null,
    };
    const data = await request("/empresas", { method: "POST", body: payload });
    setStatus("Empresa criada com sucesso.");
    showOutput(data);
    if (byId("adminEmpresaId")) byId("adminEmpresaId").value = data.id;
    if (byId("clienteEmpresaId")) byId("clienteEmpresaId").value = data.id;
    if (byId("recEmpresaId")) byId("recEmpresaId").value = data.id;
  } catch (err) {
    setStatus(err.message, false);
  }
});

onClick("btnToggleSetup", () => {
  if (!setupCard) return;
  setupCard.classList.toggle("hidden");
});
onClick("btnHideSetup", () => {
  if (setupCard) setupCard.classList.add("hidden");
});

onClick("btnBootstrap", async () => {
  try {
    const payload = {
      empresa_id: Number(byId("adminEmpresaId").value),
      nome: byId("adminNome").value,
      email: byId("adminEmail").value,
      password: byId("adminSenha").value,
      is_superuser: true,
      permissoes: [],
    };
    const data = await request("/auth/bootstrap", { method: "POST", body: payload });
    setStatus("Administrador inicial criado.");
    showOutput(data);
  } catch (err) {
    setStatus(err.message, false);
  }
});

onClick("btnLogin", async () => {
  try {
    const email = byId("loginEmail").value;
    const senha = byId("loginSenha").value;
    const form = new URLSearchParams();
    form.append("username", email);
    form.append("password", senha);

    const data = await request("/auth/login", {
      method: "POST",
      form: true,
      body: form,
    });
    setToken(data.access_token);
    setStatus("Login realizado com sucesso.");
    showOutput(data);
    refreshAuthUI();
  } catch (err) {
    setStatus(err.message, false);
  }
});

onClick("btnFillDefault", () => {
  byId("loginEmail").value = "admin@sysconta.com";
  byId("loginSenha").value = "Admin@123456";
});

moduleButtons.forEach((btn) => {
  btn.addEventListener("click", () => {
    const moduleName = btn.getAttribute("data-module");
    if (moduleName) {
      activateModule(moduleName);
    }
  });
});

onClick("btnMe", async () => {
  try {
    const data = await request("/auth/me", { auth: true });
    setStatus("Dados do usuário carregados.");
    showOutput(data);
  } catch (err) {
    setStatus(err.message, false);
  }
});

onClick("btnLogout", () => {
  clearToken();
  refreshAuthUI();
  setStatus("Sessão encerrada.");
});

onClick("btnCriarCliente", async () => {
  try {
    const payload = {
      empresa_id: Number(byId("clienteEmpresaId").value),
      tipo_documento: byId("clienteTipo").value,
      documento: byId("clienteDocumento").value,
      nome_razao: byId("clienteNome").value,
      email: byId("clienteEmail").value || null,
      telefone: byId("clienteTelefone").value || null,
      cep: byId("clienteCep").value || null,
      senha_portal: byId("clienteSenhaPortal").value || null,
    };
    const data = await request("/clientes?auto_fill_endereco=true&auto_fill_cnpj=true", {
      method: "POST",
      body: payload,
      auth: true,
    });
    setStatus("Cliente cadastrado com sucesso.");
    showOutput(data);
  } catch (err) {
    setStatus(err.message, false);
  }
});

onClick("btnListarClientes", async () => {
  try {
    const empresaId = Number(byId("clienteEmpresaId").value);
    const data = await request(`/clientes/${empresaId}`, { auth: true });
    setStatus("Clientes listados com sucesso.");
    showOutput(data);
  } catch (err) {
    setStatus(err.message, false);
  }
});

onClick("btnCriarReceber", async () => {
  try {
    const payload = {
      empresa_id: Number(byId("recEmpresaId").value),
      cliente_id: Number(byId("recClienteId").value),
      descricao: byId("recDescricao").value,
      valor: Number(byId("recValor").value),
      vencimento: byId("recVencimento").value,
    };
    const data = await request("/financeiro/contas-receber", {
      method: "POST",
      body: payload,
      auth: true,
    });
    setStatus("Conta a receber cadastrada com sucesso.");
    showOutput(data);
  } catch (err) {
    setStatus(err.message, false);
  }
});

refreshAuthUI();

if (byId("loginEmail") && !byId("loginEmail").value) {
  byId("loginEmail").value = "admin@sysconta.com";
}
if (byId("loginSenha") && !byId("loginSenha").value) {
  byId("loginSenha").value = "Admin@123456";
}
