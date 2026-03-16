const statusEl = document.getElementById("status");
const outputEl = document.getElementById("output");
const appWorkspace = document.getElementById("appWorkspace");
const authShell = document.getElementById("authShell");
const moduleButtons = document.querySelectorAll(".module-btn");
const moduleSections = document.querySelectorAll(".module-section");

const state = {
  token: localStorage.getItem("sysconta_token"),
  user: null,
  empresaId: null,
  clientes: [],
};

function byId(id) {
  return document.getElementById(id);
}

function onClick(id, handler) {
  const el = byId(id);
  if (el) el.addEventListener("click", handler);
}

function setStatus(message, ok = true) {
  if (statusEl) {
    statusEl.innerHTML = `<div class="status ${ok ? "ok" : "err"}">${message}</div>`;
  }
}

function showOutput(data) {
  if (outputEl) outputEl.textContent = JSON.stringify(data, null, 2);
}

function setToken(token) {
  state.token = token;
  localStorage.setItem("sysconta_token", token);
}

function clearToken() {
  state.token = null;
  localStorage.removeItem("sysconta_token");
}

function activateModule(moduleName) {
  moduleSections.forEach((section) => section.classList.add("hidden"));
  moduleButtons.forEach((btn) => btn.classList.remove("active"));

  if (moduleName === "cadastros") {
    byId("module-cadastros")?.classList.remove("hidden");
    byId("module-cadastros-lista")?.classList.remove("hidden");
  } else {
    byId(`module-${moduleName}`)?.classList.remove("hidden");
  }

  const active = document.querySelector(`.module-btn[data-module="${moduleName}"]`);
  if (active) active.classList.add("active");
}

function refreshAuthUI() {
  const hasToken = !!state.token;
  appWorkspace?.classList.toggle("hidden", !hasToken);
  authShell?.classList.toggle("hidden", hasToken);
  if (hasToken) activateModule("cadastros");
}

function fillUserMeta() {
  byId("metaUser").textContent = `Usuário: ${state.user?.nome || "-"}`;
  byId("metaEmpresa").textContent = `Empresa ID: ${state.empresaId || "-"}`;
}

function renderClientes() {
  const table = byId("clientesTableBody");
  const select = byId("recClienteId");
  if (!table || !select) return;

  table.innerHTML = "";
  select.innerHTML = "";

  if (state.clientes.length === 0) {
    table.innerHTML = '<tr><td colspan="5">Nenhum cliente cadastrado.</td></tr>';
    select.innerHTML = '<option value="">Sem clientes</option>';
    return;
  }

  state.clientes.forEach((cliente) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${cliente.id}</td>
      <td>${cliente.nome_razao || ""}</td>
      <td>${cliente.documento || ""}</td>
      <td>${cliente.email || ""}</td>
      <td>${cliente.telefone || ""}</td>
    `;
    table.appendChild(tr);

    const option = document.createElement("option");
    option.value = cliente.id;
    option.textContent = `${cliente.id} - ${cliente.nome_razao}`;
    select.appendChild(option);
  });
}

async function request(path, { method = "GET", body, auth = false, form = false } = {}) {
  const headers = {};
  if (auth && state.token) headers.Authorization = `Bearer ${state.token}`;
  if (!form) headers["Content-Type"] = "application/json";

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
  if (!res.ok) throw new Error(data.detail || data.message || `Erro ${res.status}`);
  return data;
}

async function loadMeAndClientes() {
  state.user = await request("/auth/me", { auth: true });
  state.empresaId = state.user.empresa_id;
  fillUserMeta();

  const clientes = await request(`/clientes/${state.empresaId}`, { auth: true });
  state.clientes = Array.isArray(clientes) ? clientes : [];
  renderClientes();
}

onClick("btnLogin", async () => {
  try {
    const form = new URLSearchParams();
    form.append("username", byId("loginEmail").value);
    form.append("password", byId("loginSenha").value);
    const data = await request("/auth/login", { method: "POST", body: form, form: true });
    setToken(data.access_token);
    await loadMeAndClientes();
    refreshAuthUI();
    setStatus("Login realizado com sucesso.");
    showOutput(data);
  } catch (err) {
    setStatus(err.message, false);
  }
});

onClick("btnFillDefault", () => {
  byId("loginEmail").value = "admin@sysconta.com";
  byId("loginSenha").value = "Admin@123456";
});

onClick("btnLogout", () => {
  clearToken();
  state.user = null;
  state.empresaId = null;
  state.clientes = [];
  refreshAuthUI();
  setStatus("Sessão encerrada.");
});

onClick("btnCriarCliente", async () => {
  try {
    if (!state.empresaId) throw new Error("Faça login novamente.");
    const payload = {
      empresa_id: state.empresaId,
      tipo_documento: byId("clienteTipo").value,
      documento: byId("clienteDocumento").value,
      nome_razao: byId("clienteNome").value,
      email: byId("clienteEmail").value || null,
      telefone: byId("clienteTelefone").value || null,
      cep: byId("clienteCep").value || null,
      endereco: byId("clienteEndereco").value || null,
      numero: byId("clienteNumero").value || null,
      bairro: byId("clienteBairro").value || null,
      cidade: byId("clienteCidade").value || null,
      estado: byId("clienteEstado").value || null,
      senha_portal: byId("clienteSenhaPortal").value || null,
    };
    const data = await request("/clientes?auto_fill_endereco=true&auto_fill_cnpj=true", {
      method: "POST",
      body: payload,
      auth: true,
    });
    setStatus("Cliente cadastrado com sucesso.");
    showOutput(data);
    await loadMeAndClientes();
  } catch (err) {
    setStatus(err.message, false);
  }
});

onClick("btnListarClientes", async () => {
  try {
    await loadMeAndClientes();
    setStatus("Lista de clientes atualizada.");
  } catch (err) {
    setStatus(err.message, false);
  }
});

onClick("btnCriarReceber", async () => {
  try {
    if (!state.empresaId) throw new Error("Faça login novamente.");
    const payload = {
      empresa_id: state.empresaId,
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

moduleButtons.forEach((btn) => {
  btn.addEventListener("click", () => {
    const moduleName = btn.getAttribute("data-module");
    if (moduleName) activateModule(moduleName);
  });
});

refreshAuthUI();

if (byId("recVencimento")) {
  byId("recVencimento").value = new Date().toISOString().slice(0, 10);
}
if (byId("loginEmail") && !byId("loginEmail").value) {
  byId("loginEmail").value = "admin@sysconta.com";
}
if (byId("loginSenha") && !byId("loginSenha").value) {
  byId("loginSenha").value = "Admin@123456";
}
