/* PORTAL-NEXT V2 — Painel Master / Admin Foundation (Painel Master
   Phase 2A). Business logic: none here — this file only orchestrates
   the real, already-audited admin RPCs (via
   assets/js/adapters/master-users-provider.js +
   master-users-view-model.js). Full RPC contract:
   docs/MASTER-USERS-RPC-CONTRACT-CAPTURE.md.

   Route guard: shell.js's router already enforces MASTER_ONLY
   (auth-core.js's isModuleAuthorized) BEFORE this module's render() is
   ever called — this file does not re-implement that check (Gate:
   "não duplicar regra administrativa no frontend"). The real RPCs also
   independently re-verify MASTER server-side regardless (defense in
   depth, already proven in Phase 0/1's audit) — this file trusts
   neither its own nor the router's check as the actual authority.

   Information architecture (Gate 9): six real clusters exist
   (Usuários & Acesso / Governança de Dados / Comissões & RH /
   Simuladores / Auditoria / Futuras Funcionalidades — Phase 0/1 Gate
   4). Only "Usuários" is implemented this Phase; the section-nav
   below is built to add sections without restructuring (MIGRATED_SCOPE
   = USERS_ONLY).

   Router note: this SPA's router is flat (one hash segment per
   registry entry id, "#/shell-admin" — the registry's own "route":
   "/admin" field is documentation-only, never read by code, confirmed
   Phase 2A Gate 5 research). "Subrotas" are therefore internal view
   state (currentSection/currentView below), not a second hash-routing
   layer — this is the correct, evidence-based choice, not an
   improvisation (no nested-route mechanism exists anywhere in this
   codebase to reuse, and building one would be exactly the kind of new
   parallel architecture this Phase is instructed to avoid).

   Real-mode only (Gate 28): unlike the analytical modules, Usuários
   has no natural "fixture scenario" concept (it is not a calculation
   engine over varying datasets — it is one real administrative
   dataset). Deterministic tests mock the transport at the network
   layer (Playwright route()), the same technique already proven for
   every real-provider-test.py in this codebase, rather than adding a
   redundant JS-level fixture toggle here. */
(function () {
  'use strict';

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c] || c;
    });
  }

  // ---------- module state ----------
  var currentSection = 'usuarios'; // only implemented section this Phase
  var currentView = 'list'; // 'list' | 'detail' | 'create'
  var usersRows = [];
  var currentDetailId = null;
  var searchQuery = '';
  var filterPerfil = '';
  var filterLoja = '';
  var filterStatus = ''; // '' = all, 'ATIVO', 'INATIVO'
  var renderSeq = 0;
  var currentAbortController = null;
  var loadError = null;
  var isLoading = false;

  // Double-submit guards (Gate 24) — one per distinct mutation action,
  // never a single shared flag (two different actions must not block
  // each other).
  var inFlight = { invite: false, edit: false, toggleActive: false, resend: false };

  // Create/Edit form working state — reset on view change.
  var createForm = null;
  var editForm = null;
  var pendingConfirm = null; // {kind, payload} while a confirm step is shown

  // Gate 22 error-state vocabulary (transport-level, from the
  // provider's classifyError) + Gate 6 client-side VALIDATION_ERROR
  // (never sent to the RPC at all).
  var STATE_COPY = {
    AUTH_DENIED: { title: 'Sem permissão', body: 'Sua conta não tem acesso a esta área.' },
    SESSION_EXPIRED: { title: 'Sessão expirada', body: 'Entre novamente para continuar.' },
    RPC_ERROR: { title: 'Não foi possível concluir', body: 'Não foi possível concluir a operação agora. Tente novamente.' },
    NETWORK_ERROR: { title: 'Falha de rede', body: 'Verifique sua conexão e tente novamente.' },
    TIMEOUT: { title: 'Tempo excedido', body: 'A resposta demorou demais. Tente novamente.' },
    MALFORMED_RESPONSE: { title: 'Não foi possível carregar', body: 'Resposta inesperada do servidor.' },
    VALIDATION_ERROR: { title: 'Dados inválidos', body: 'Verifique os campos destacados.' },
    DUPLICATE_USER: { title: 'Usuário já existe', body: 'Já existe um cadastro com este CPF ou e-mail.' },
    CONFLICT: { title: 'Não foi possível concluir', body: 'Esta ação não pode ser concluída no estado atual do cadastro.' }
  };
  function errorStateHtml(state, message) {
    var copy = STATE_COPY[state] || STATE_COPY.RPC_ERROR;
    return '<div class="modErrorState"><div class="modStateTitle">' + esc(copy.title) + '</div>' + esc(copy.body) + '</div>';
  }
  function loadingHtml() {
    return '<div class="modLoadingState"><span class="modLoadingDot"></span>Carregando usuários...</div>';
  }

  function rowById(id) {
    return usersRows.filter(function (r) { return r.id === id; })[0] || null;
  }

  // ---------- filtering (Gate 13: client-side over the one fully-
  // authorized dataset the RPC already returns — same technique V1
  // itself uses, confirmed equivalent in Phase 0/1's audit) ----------
  function filteredRows() {
    var q = searchQuery.trim().toLowerCase();
    return usersRows.filter(function (r) {
      if (filterPerfil && r.perfil !== filterPerfil) return false;
      if (filterLoja && r.loja !== filterLoja) return false;
      if (filterStatus === 'ATIVO' && !r.ativo) return false;
      if (filterStatus === 'INATIVO' && r.ativo) return false;
      if (q && r.nome.toLowerCase().indexOf(q) === -1 && r.emailAuth.toLowerCase().indexOf(q) === -1) return false;
      return true;
    });
  }

  // ---------- data load (Gate 41: the one real read-only call) ----------
  function loadUsers() {
    if (currentAbortController) currentAbortController.abort();
    var controller = new AbortController();
    currentAbortController = controller;
    var mySeq = ++renderSeq;
    loadError = null;
    isLoading = true;
    renderPanel();

    window.NX_MASTER_USERS_PROVIDER.loadMasterUsersData({ signal: controller.signal }).then(
      function (payload) {
        if (mySeq !== renderSeq) return;
        isLoading = false;
        var vm = window.NX_MASTER_USERS_VIEW_MODEL.buildUsersViewModel(payload);
        usersRows = vm.rows;
        renderPanel();
      },
      function (err) {
        if (mySeq !== renderSeq) return;
        if (err && err.state === 'ABORTED') return;
        isLoading = false;
        loadError = err || { state: 'RPC_ERROR' };
        renderPanel();
      }
    );
  }

  // ---------- lifecycle badge ----------
  function lifecycleBadgeHtml(lifecycle) {
    var cls = {
      INVITED: 'maBadgeInvited', AUTH_CREATED_UNCONFIRMED: 'maBadgeInvited',
      FIRST_ACCESS_PENDING: 'maBadgePending', ACTIVE: 'maBadgeActive', INACTIVE: 'maBadgeInactive'
    }[lifecycle.state] || 'maBadgeInactive';
    return '<span class="maBadge ' + cls + '">' + esc(lifecycle.label) + '</span>';
  }

  function rowKey(r) { return r.id; }

  // ---------- list rendering (desktop table + mobile cards, Score's
  // established dual-renderer pattern — one `rows` array, two views,
  // exactly one visible via CSS) ----------
  function renderDesktopTable(rows) {
    var body = rows.map(function (r) {
      return '<tr tabindex="0" role="button" data-key="' + esc(rowKey(r)) + '" aria-label="Ver detalhes de ' + esc(r.nome) + '">' +
        '<td class="maNameCell">' + esc(r.nome) + '<div class="maSubtle">' + esc(r.emailAuth) + '</div></td>' +
        '<td>' + esc(r.perfil) + '</td>' +
        '<td>' + esc(r.loja || '—') + '</td>' +
        '<td>' + esc(r.status || '—') + '</td>' +
        '<td>' + lifecycleBadgeHtml(r.lifecycle) + '</td>' +
        '</tr>';
    }).join('');
    return '<div class="maDesktopOnly"><div class="modTableWrap"><table class="modTable maTable">' +
      '<thead><tr><th scope="col">Usuário</th><th scope="col">Perfil</th><th scope="col">Loja</th><th scope="col">Status</th><th scope="col">Situação</th></tr></thead>' +
      '<tbody>' + body + '</tbody></table></div></div>';
  }
  function renderMobileCards(rows) {
    var cards = rows.map(function (r) {
      return '<div class="maMobileCard" tabindex="0" role="button" data-key="' + esc(rowKey(r)) + '" aria-label="Ver detalhes de ' + esc(r.nome) + '">' +
        '<div class="maMobileName">' + esc(r.nome) + '</div>' +
        '<div class="maSubtle">' + esc(r.emailAuth) + '</div>' +
        '<div class="maMobileMeta">' + esc(r.perfil) + ' · ' + esc(r.loja || '—') + ' · ' + esc(r.status || '—') + '</div>' +
        lifecycleBadgeHtml(r.lifecycle) +
        '</div>';
    }).join('');
    return '<div class="maMobileOnly">' + cards + '</div>';
  }
  function renderList() {
    var rows = filteredRows();
    var tableHtml;
    if (!rows.length) {
      tableHtml = '<div class="modEmptyState"><div class="modStateTitle">Nenhum usuário encontrado</div>Ajuste a busca ou os filtros.</div>';
    } else {
      tableHtml = renderDesktopTable(rows) + renderMobileCards(rows);
    }
    var perfilOptions = ['<option value="">Todos os perfis</option>'].concat(
      window.NX_MASTER_USERS_VIEW_MODEL.PERFIL_VALUES.map(function (p) { return '<option value="' + esc(p) + '"' + (p === filterPerfil ? ' selected' : '') + '>' + esc(p) + '</option>'; })
    ).join('');
    var lojaOptions = ['<option value="">Todas as lojas</option>'].concat(
      window.NX_MASTER_USERS_VIEW_MODEL.LOJA_VALUES.map(function (l) { return '<option value="' + esc(l) + '"' + (l === filterLoja ? ' selected' : '') + '>' + esc(l) + '</option>'; })
    ).join('');
    return '<div class="modFilters">' +
      '<div class="modField"><label for="maSearch">Buscar</label><input id="maSearch" type="text" value="' + esc(searchQuery) + '" placeholder="Nome ou e-mail"></div>' +
      '<div class="modField"><label for="maFilterPerfil">Perfil</label><select id="maFilterPerfil">' + perfilOptions + '</select></div>' +
      '<div class="modField"><label for="maFilterLoja">Loja</label><select id="maFilterLoja">' + lojaOptions + '</select></div>' +
      '<div class="modField"><label for="maFilterStatus">Situação</label><select id="maFilterStatus">' +
      '<option value=""' + (!filterStatus ? ' selected' : '') + '>Todos</option>' +
      '<option value="ATIVO"' + (filterStatus === 'ATIVO' ? ' selected' : '') + '>Ativos</option>' +
      '<option value="INATIVO"' + (filterStatus === 'INATIVO' ? ' selected' : '') + '>Inativos</option>' +
      '</select></div>' +
      '</div>' + tableHtml;
  }

  // ---------- detail / edit ----------
  function fieldRow(label, value) {
    return '<div class="maDetailField"><span class="maDetailLabel">' + esc(label) + '</span><span class="maDetailValue">' + esc(value) + '</span></div>';
  }
  function renderDetail(r) {
    if (!r) return '';
    var editing = editForm && editForm.id === r.id;
    var body;
    if (editing) {
      body = renderEditForm(r);
    } else {
      body = fieldRow('Nome', r.nome) + fieldRow('E-mail', r.emailAuth) + fieldRow('CPF', r.cpfMasked) +
        fieldRow('Perfil', r.perfil) + fieldRow('Loja', r.loja || '—') + fieldRow('Departamento', r.status || '—') +
        '<div class="maDetailField"><span class="maDetailLabel">Situação</span>' + lifecycleBadgeHtml(r.lifecycle) + '</div>' +
        (r.emailDivergente ? '<p class="maWarnNote">O e-mail de autenticação diverge do e-mail cadastrado.</p>' : '') +
        '<div class="maDetailActions">' +
        '<button type="button" class="modBtn" id="maEditBtn">Editar autorização</button>' +
        '<button type="button" class="modBtn' + (r.ativo ? ' modBtnDanger' : '') + '" id="maToggleActiveBtn">' + (r.ativo ? 'Bloquear' : 'Reativar') + '</button>' +
        (r.conviteId ? '<button type="button" class="modBtn" id="maResendBtn">Reenviar convite</button>' : '') +
        '</div>';
    }
    return '<div class="maDetail" id="maDetail">' +
      '<div class="maDetailHead"><h2>' + esc(r.nome) + '</h2>' +
      '<button type="button" class="modBtnGhost" id="maCloseDetail">Fechar</button></div>' +
      body + '</div>';
  }

  function renderEditForm(r) {
    var perfilOptions = window.NX_MASTER_USERS_VIEW_MODEL.PERFIL_VALUES.map(function (p) {
      return '<option value="' + esc(p) + '"' + (p === editForm.perfil ? ' selected' : '') + '>' + esc(p) + '</option>';
    }).join('');
    var lojaOptions = ['<option value="">—</option>'].concat(
      window.NX_MASTER_USERS_VIEW_MODEL.LOJA_VALUES.map(function (l) { return '<option value="' + esc(l) + '"' + (l === editForm.loja ? ' selected' : '') + '>' + esc(l) + '</option>'; })
    ).join('');
    var statusOptions = ['<option value="">—</option>'].concat(
      window.NX_MASTER_USERS_VIEW_MODEL.STATUS_VALUES.map(function (s) { return '<option value="' + esc(s) + '"' + (s === editForm.status ? ' selected' : '') + '>' + esc(s) + '</option>'; })
    ).join('');
    return '<form id="maEditForm" novalidate>' +
      '<div class="modField"><label for="maEditPerfil">Perfil</label><select id="maEditPerfil">' + perfilOptions + '</select></div>' +
      '<div class="modField"><label for="maEditLoja">Loja</label><select id="maEditLoja">' + lojaOptions + '</select></div>' +
      '<div class="modField"><label for="maEditStatus">Departamento</label><select id="maEditStatus">' + statusOptions + '</select></div>' +
      (editForm.error ? '<p class="maFieldError" role="alert">' + esc(editForm.error) + '</p>' : '') +
      '<div class="maDetailActions">' +
      '<button type="submit" class="modBtn" id="maEditSubmit"' + (inFlight.edit ? ' disabled' : '') + '>Salvar alterações</button>' +
      '<button type="button" class="modBtnGhost" id="maEditCancel">Cancelar</button>' +
      '</div></form>';
  }

  // ---------- create/invite ----------
  function emptyCreateForm() {
    return { cpf: '', nome: '', perfil: '', loja: '', email: '', nbs: '', status: '', error: null };
  }
  function renderCreateView() {
    var f = createForm;
    var perfilOptions = ['<option value="">Selecione...</option>'].concat(
      window.NX_MASTER_USERS_VIEW_MODEL.PERFIL_VALUES.map(function (p) { return '<option value="' + esc(p) + '"' + (p === f.perfil ? ' selected' : '') + '>' + esc(p) + '</option>'; })
    ).join('');
    var lojaOptions = ['<option value="">—</option>'].concat(
      window.NX_MASTER_USERS_VIEW_MODEL.LOJA_VALUES.map(function (l) { return '<option value="' + esc(l) + '"' + (l === f.loja ? ' selected' : '') + '>' + esc(l) + '</option>'; })
    ).join('');
    var statusRequired = window.NX_MASTER_USERS_VIEW_MODEL.STATUS_REQUIRED_PROFILES.indexOf(f.perfil) !== -1;
    var statusOptions = ['<option value="">Selecione...</option>'].concat(
      window.NX_MASTER_USERS_VIEW_MODEL.STATUS_VALUES.map(function (s) { return '<option value="' + esc(s) + '"' + (s === f.status ? ' selected' : '') + '>' + esc(s) + '</option>'; })
    ).join('');
    return '<div class="maDetail" id="maCreateView">' +
      '<div class="maDetailHead"><h2>Novo usuário</h2><button type="button" class="modBtnGhost" id="maCreateCancel">Cancelar</button></div>' +
      '<form id="maCreateForm" novalidate>' +
      '<div class="modField"><label for="maCpf">CPF</label><input id="maCpf" type="text" value="' + esc(f.cpf) + '" inputmode="numeric"></div>' +
      '<div class="modField"><label for="maNome">Nome</label><input id="maNome" type="text" value="' + esc(f.nome) + '"></div>' +
      '<div class="modField"><label for="maPerfil">Perfil</label><select id="maPerfil">' + perfilOptions + '</select></div>' +
      '<div class="modField"><label for="maLoja">Loja</label><select id="maLoja">' + lojaOptions + '</select></div>' +
      '<div class="modField"><label for="maEmail">E-mail</label><input id="maEmail" type="email" value="' + esc(f.email) + '"></div>' +
      '<div class="modField"><label for="maNbs">Login NBS (opcional)</label><input id="maNbs" type="text" value="' + esc(f.nbs) + '"></div>' +
      (statusRequired ? '<div class="modField"><label for="maStatus">Departamento</label><select id="maStatus">' + statusOptions + '</select></div>' : '') +
      (f.error ? '<p class="maFieldError" role="alert">' + esc(f.error) + '</p>' : '') +
      '<div class="maDetailActions">' +
      '<button type="submit" class="modBtn" id="maCreateSubmit"' + (inFlight.invite ? ' disabled' : '') + '>Convidar usuário</button>' +
      '</div></form></div>';
  }

  // ---------- confirmation step (inline, two-step reveal — no modal
  // primitive exists yet in this codebase; Gate 10 forbids introducing
  // a new parallel component for this alone) ----------
  function confirmHtml(title, body, confirmLabel, destructive) {
    return '<div class="maConfirm" role="alertdialog" aria-labelledby="maConfirmTitle">' +
      '<h3 id="maConfirmTitle">' + esc(title) + '</h3><p>' + esc(body) + '</p>' +
      '<div class="maDetailActions">' +
      '<button type="button" class="modBtn' + (destructive ? ' modBtnDanger' : '') + '" id="maConfirmYes">' + esc(confirmLabel) + '</button>' +
      '<button type="button" class="modBtnGhost" id="maConfirmNo">Cancelar</button>' +
      '</div></div>';
  }

  // ---------- section nav (Gate 9: structure ready for future
  // clusters without rewrite) ----------
  var SECTIONS = [
    { id: 'usuarios', label: 'Usuários', active: true },
    { id: 'acessos', label: 'Acessos aos Módulos', active: false },
    { id: 'auditoria', label: 'Auditoria', active: false },
    { id: 'revisoes', label: 'Revisões Cadastrais', active: false }
  ];
  function sectionNavHtml() {
    return '<nav class="maSectionNav" aria-label="Áreas administrativas">' + SECTIONS.map(function (s) {
      if (!s.active) {
        return '<span class="maSectionItem maSectionItemDisabled" aria-disabled="true">' + esc(s.label) + ' <span class="maSectionSoon">Em breve</span></span>';
      }
      return '<span class="maSectionItem maSectionItemActive" aria-current="page">' + esc(s.label) + '</span>';
    }).join('') + '</nav>';
  }

  // ---------- master render ----------
  function renderPanel() {
    var panel = document.getElementById('maPanel');
    if (!panel) return;

    if (loadError) {
      panel.innerHTML = errorStateHtml(loadError.state, loadError.message);
      return;
    }
    if (isLoading && currentView === 'list') {
      panel.innerHTML = loadingHtml();
      return;
    }

    var html = '';
    if (currentView === 'create') {
      html = renderCreateView();
    } else {
      html = renderList();
      var detailRow = currentDetailId ? rowById(currentDetailId) : null;
      html += detailRow ? renderDetail(detailRow) : '';
    }
    if (pendingConfirm) {
      html += confirmHtml(pendingConfirm.title, pendingConfirm.body, pendingConfirm.confirmLabel, pendingConfirm.destructive);
    }
    panel.innerHTML = html;
    wireInteraction();
  }

  // ---------- interaction wiring ----------
  function openDetail(id) { currentDetailId = id; editForm = null; pendingConfirm = null; renderPanel(); }
  function closeDetail() { currentDetailId = null; editForm = null; pendingConfirm = null; renderPanel(); }

  function wireInteraction() {
    document.querySelectorAll('.maTable tbody tr, .maMobileCard').forEach(function (el) {
      el.addEventListener('click', function () { openDetail(el.getAttribute('data-key')); });
      el.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); openDetail(el.getAttribute('data-key')); }
      });
    });

    var search = document.getElementById('maSearch');
    if (search) search.addEventListener('input', function (e) { searchQuery = e.target.value; renderPanel(); });
    var fp = document.getElementById('maFilterPerfil');
    if (fp) fp.addEventListener('change', function (e) { filterPerfil = e.target.value; renderPanel(); });
    var fl = document.getElementById('maFilterLoja');
    if (fl) fl.addEventListener('change', function (e) { filterLoja = e.target.value; renderPanel(); });
    var fs = document.getElementById('maFilterStatus');
    if (fs) fs.addEventListener('change', function (e) { filterStatus = e.target.value; renderPanel(); });

    var closeBtn = document.getElementById('maCloseDetail');
    if (closeBtn) closeBtn.addEventListener('click', closeDetail);

    var editBtn = document.getElementById('maEditBtn');
    if (editBtn) editBtn.addEventListener('click', function () {
      var r = rowById(currentDetailId);
      editForm = { id: r.id, perfil: r.perfil, loja: r.loja, status: r.status, ativo: r.ativo, error: null };
      renderPanel();
    });
    var editCancel = document.getElementById('maEditCancel');
    if (editCancel) editCancel.addEventListener('click', function () { editForm = null; renderPanel(); });
    var editPerfil = document.getElementById('maEditPerfil');
    if (editPerfil) editPerfil.addEventListener('change', function (e) { editForm.perfil = e.target.value; });
    var editLoja = document.getElementById('maEditLoja');
    if (editLoja) editLoja.addEventListener('change', function (e) { editForm.loja = e.target.value; });
    var editStatus = document.getElementById('maEditStatus');
    if (editStatus) editStatus.addEventListener('change', function (e) { editForm.status = e.target.value; });
    var editForm2 = document.getElementById('maEditForm');
    if (editForm2) editForm2.addEventListener('submit', function (e) {
      e.preventDefault();
      pendingConfirm = {
        kind: 'edit',
        title: 'Confirmar alteração de autorização',
        body: 'Perfil: ' + editForm.perfil + ' · Loja: ' + (editForm.loja || '—') + ' · Departamento: ' + (editForm.status || '—'),
        confirmLabel: 'Confirmar', destructive: false
      };
      renderPanel();
    });

    var toggleBtn = document.getElementById('maToggleActiveBtn');
    if (toggleBtn) toggleBtn.addEventListener('click', function () {
      var r = rowById(currentDetailId);
      pendingConfirm = {
        kind: 'toggleActive', target: r,
        title: r.ativo ? 'Bloquear usuário' : 'Reativar usuário',
        body: r.ativo ? 'O usuário perderá acesso imediatamente ao portal.' : 'O usuário voltará a ter acesso ao portal.',
        confirmLabel: r.ativo ? 'Bloquear' : 'Reativar', destructive: r.ativo
      };
      renderPanel();
    });

    var resendBtn = document.getElementById('maResendBtn');
    if (resendBtn) resendBtn.addEventListener('click', function () {
      var r = rowById(currentDetailId);
      pendingConfirm = {
        kind: 'resend', target: r,
        title: 'Reenviar convite',
        body: 'Um novo e-mail de convite será enviado para ' + r.emailAuth + '.',
        confirmLabel: 'Reenviar', destructive: false
      };
      renderPanel();
    });

    var confirmYes = document.getElementById('maConfirmYes');
    if (confirmYes) confirmYes.addEventListener('click', executeConfirmedAction);
    var confirmNo = document.getElementById('maConfirmNo');
    if (confirmNo) confirmNo.addEventListener('click', function () { pendingConfirm = null; renderPanel(); });

    // ---- create/invite ----
    var newBtn = document.getElementById('maNewUserBtn');
    if (newBtn) newBtn.addEventListener('click', function () { createForm = emptyCreateForm(); currentView = 'create'; currentDetailId = null; renderPanel(); });
    var createCancel = document.getElementById('maCreateCancel');
    if (createCancel) createCancel.addEventListener('click', function () { currentView = 'list'; createForm = null; renderPanel(); });
    ['maCpf', 'maNome', 'maEmail', 'maNbs'].forEach(function (id) {
      var el = document.getElementById(id);
      if (el) el.addEventListener('input', function (e) { createForm[id.replace('ma', '').toLowerCase()] = e.target.value; });
    });
    var cPerfil = document.getElementById('maPerfil');
    if (cPerfil) cPerfil.addEventListener('change', function (e) { createForm.perfil = e.target.value; createForm.status = ''; renderPanel(); });
    var cLoja = document.getElementById('maLoja');
    if (cLoja) cLoja.addEventListener('change', function (e) { createForm.loja = e.target.value; });
    var cStatus = document.getElementById('maStatus');
    if (cStatus) cStatus.addEventListener('change', function (e) { createForm.status = e.target.value; });
    var createFormEl = document.getElementById('maCreateForm');
    if (createFormEl) createFormEl.addEventListener('submit', function (e) {
      e.preventDefault();
      var err = validateCreateForm(createForm);
      if (err) { createForm.error = err; renderPanel(); return; }
      createForm.error = null;
      pendingConfirm = {
        kind: 'invite',
        title: 'Confirmar convite',
        body: createForm.nome + ' (' + createForm.perfil + ') — ' + createForm.email,
        confirmLabel: 'Enviar convite', destructive: false
      };
      renderPanel();
    });
  }

  // Gate 17: UX-only echo of the real RPC's own authoritative
  // validation (docs/MASTER-USERS-RPC-CONTRACT-CAPTURE.md) — no new
  // business rule invented; the RPC remains the final authority
  // regardless of what passes here.
  function validateCreateForm(f) {
    var cpfDigits = f.cpf.replace(/\D/g, '');
    if (!cpfDigits || cpfDigits.length > 11) return 'CPF inválido.';
    if (!f.nome.trim()) return 'Nome é obrigatório.';
    if (!f.perfil) return 'Selecione um perfil.';
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(f.email)) return 'E-mail inválido.';
    if (window.NX_MASTER_USERS_VIEW_MODEL.STATUS_REQUIRED_PROFILES.indexOf(f.perfil) !== -1 && !f.status) {
      return 'Selecione o departamento para este perfil.';
    }
    return null;
  }

  // ---------- mutation execution (Gate 16/47: WIRED, NEVER CALLED
  // during this Phase's own execution — this function exists and is
  // exercised only by mocked deterministic tests,
  // tests/master-users-*.py). Double-submit guarded regardless. ----------
  function executeConfirmedAction() {
    if (!pendingConfirm) return;
    var kind = pendingConfirm.kind;
    var flagKey = kind === 'toggleActive' ? 'toggleActive' : kind === 'resend' ? 'resend' : kind === 'edit' ? 'edit' : 'invite';
    if (inFlight[flagKey]) return; // double-submit guard
    inFlight[flagKey] = true;

    var provider = window.NX_MASTER_USERS_PROVIDER;
    var promise;
    if (kind === 'invite') {
      promise = provider.inviteUser(createForm, {});
    } else if (kind === 'edit') {
      var r = rowById(editForm.id);
      promise = provider.updateUserAuthorization({ usuarioId: editForm.id, perfil: editForm.perfil, loja: editForm.loja, status: editForm.status, ativo: r.ativo }, {});
    } else if (kind === 'toggleActive') {
      var t = pendingConfirm.target;
      promise = provider.updateUserAuthorization({ usuarioId: t.id, perfil: t.perfil, loja: t.loja, status: t.status, ativo: !t.ativo }, {});
    } else if (kind === 'resend') {
      promise = provider.resendInvite(pendingConfirm.target.conviteId, {});
    }

    promise.then(
      function () {
        inFlight[flagKey] = false;
        pendingConfirm = null;
        currentView = 'list';
        createForm = null;
        editForm = null;
        loadUsers(); // re-fetch authoritative state, never optimistic
      },
      function (err) {
        inFlight[flagKey] = false;
        if (kind === 'invite') { createForm.error = (STATE_COPY[err && err.state] || STATE_COPY.RPC_ERROR).body; }
        else if (kind === 'edit') { editForm.error = (STATE_COPY[err && err.state] || STATE_COPY.RPC_ERROR).body; }
        pendingConfirm = null;
        renderPanel();
      }
    );
  }

  window.NX_SHELL_ADMIN_PAGE = {
    render: function (outlet) {
      currentView = 'list';
      currentDetailId = null;
      searchQuery = ''; filterPerfil = ''; filterLoja = ''; filterStatus = '';
      loadError = null;
      usersRows = [];
      renderSeq = 0;
      isLoading = false;
      outlet.innerHTML =
        '<div class="maPage">' +
        '<div class="modPageHeader"><div class="modHeaderMain"><h1 class="modTitle">Painel Master</h1><p class="modSubtitle">Administração de usuários e acessos.</p></div>' +
        '<button type="button" class="modBtn" id="maNewUserBtn">+ Novo usuário</button></div>' +
        sectionNavHtml() +
        '<div id="maPanel"></div>' +
        '</div>';
      document.getElementById('maNewUserBtn').addEventListener('click', function () { createForm = emptyCreateForm(); currentView = 'create'; renderPanel(); });
      loadUsers();
      return Promise.resolve();
    }
  };
})();