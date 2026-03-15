const statusEl = document.getElementById("status");
const outputEl = document.getElementById("output");
const appCard = document.getElementById("appCard");
const clienteCard = document.getElementById("clienteCard");
const financeiroCard = document.getElementById("financeiroCard");

function setStatus(message, ok = true) {
  statusEl.innerHTML = `<div class="status ${ok ? "ok" : "err"}">${message}</div>`;
}

function showOutput(data) {
  outputEl.textContent = JSON.stringify(data, null, 2);
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

function refreshAuthUI() {
  const hasToken = !!getToken();
  appCard.classList.toggle("hidden", !hasToken);
  clienteCard.classList.toggle("hidden", !hasToken);
  financeiroCard.classList.toggle("hidden", !hasToken);
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

document.getElementById("btnCriarEmpresa").addEventListener("click", async () => {
  try {
    const payload = {
      nome: document.getElementById("empresaNome").value,
      cnpj: document.getElementById("empresaCnpj").value || null,
    };
    const data = await request("/empresas", { method: "POST", body: payload });
    setStatus("Empresa criada com sucesso.");
    showOutput(data);
    document.getElementById("adminEmpresaId").value = data.id;
    document.getElementById("clienteEmpresaId").value = data.id;
    document.getElementById("recEmpresaId").value = data.id;
  } catch (err) {
    setStatus(err.message, false);
  }
});

document.getElementById("btnBootstrap").addEventListener("click", async () => {
  try {
    const payload = {
      empresa_id: Number(document.getElementById("adminEmpresaId").value),
      nome: document.getElementById("adminNome").value,
      email: document.getElementById("adminEmail").value,
      password: document.getElementById("adminSenha").value,
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

document.getElementById("btnLogin").addEventListener("click", async () => {
  try {
    const email = document.getElementById("loginEmail").value;
    const senha = document.getElementById("loginSenha").value;
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

document.getElementById("btnMe").addEventListener("click", async () => {
  try {
    const data = await request("/auth/me", { auth: true });
    setStatus("Dados do usuário carregados.");
    showOutput(data);
  } catch (err) {
    setStatus(err.message, false);
  }
});

document.getElementById("btnLogout").addEventListener("click", () => {
  clearToken();
  refreshAuthUI();
  setStatus("Sessão encerrada.");
});

document.getElementById("btnCriarCliente").addEventListener("click", async () => {
  try {
    const payload = {
      empresa_id: Number(document.getElementById("clienteEmpresaId").value),
      tipo_documento: document.getElementById("clienteTipo").value,
      documento: document.getElementById("clienteDocumento").value,
      nome_razao: document.getElementById("clienteNome").value,
      email: document.getElementById("clienteEmail").value || null,
      telefone: document.getElementById("clienteTelefone").value || null,
      cep: document.getElementById("clienteCep").value || null,
      senha_portal: document.getElementById("clienteSenhaPortal").value || null,
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

document.getElementById("btnListarClientes").addEventListener("click", async () => {
  try {
    const empresaId = Number(document.getElementById("clienteEmpresaId").value);
    const data = await request(`/clientes/${empresaId}`, { auth: true });
    setStatus("Clientes listados com sucesso.");
    showOutput(data);
  } catch (err) {
    setStatus(err.message, false);
  }
});

document.getElementById("btnCriarReceber").addEventListener("click", async () => {
  try {
    const payload = {
      empresa_id: Number(document.getElementById("recEmpresaId").value),
      cliente_id: Number(document.getElementById("recClienteId").value),
      descricao: document.getElementById("recDescricao").value,
      valor: Number(document.getElementById("recValor").value),
      vencimento: document.getElementById("recVencimento").value,
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
