// transfer.js — Real-time account lookup and transfer form logic

document.addEventListener('DOMContentLoaded', () => {
  const toInput    = document.getElementById('to_account_number');
  const lookupInfo = document.getElementById('lookupInfo');
  const amountInput= document.getElementById('amount');
  const fromSelect = document.getElementById('from_account');
  const balanceHint= document.getElementById('balanceHint');

  let lookupTimer = null;

  // ── Real-time account lookup ──
  if (toInput) {
    toInput.addEventListener('input', () => {
      const val = toInput.value.trim();
      clearTimeout(lookupTimer);
      if (lookupInfo) lookupInfo.innerHTML = '';

      if (val.length < 5) return;

      lookupTimer = setTimeout(async () => {
        lookupInfo.innerHTML = `<span style="color:var(--text-muted);font-size:12px">
          <i class="bi bi-hourglass-split"></i> Recherche...</span>`;
        try {
          const res  = await fetch(`/api/account-lookup/${encodeURIComponent(val)}`);
          const data = await res.json();
          if (data.found) {
            lookupInfo.innerHTML = `
              <div style="background:rgba(0,201,167,0.1);border:1px solid rgba(0,201,167,0.25);
                          border-radius:8px;padding:10px 14px;margin-top:8px;">
                <div style="font-size:12px;color:var(--teal);font-weight:600;">
                  <i class="bi bi-check-circle"></i> Compte trouvé
                </div>
                <div style="font-size:13px;color:var(--text);margin-top:4px;">
                  <strong>${data.owner}</strong>
                  <span style="color:var(--text-muted);margin-left:8px;">
                    (${data.type === 'courant' ? 'Compte Courant' : 'Compte Épargne'})
                  </span>
                </div>
              </div>`;
          } else {
            lookupInfo.innerHTML = `
              <div style="background:rgba(255,71,87,0.1);border:1px solid rgba(255,71,87,0.25);
                          border-radius:8px;padding:10px 14px;margin-top:8px;">
                <div style="font-size:12px;color:var(--danger);font-weight:600;">
                  <i class="bi bi-x-circle"></i> Compte introuvable
                </div>
              </div>`;
          }
        } catch {
          lookupInfo.innerHTML = `<span style="color:var(--danger);font-size:12px">Erreur de connexion</span>`;
        }
      }, 600);
    });
  }

  // ── Show balance hint when account is selected ──
  if (fromSelect && balanceHint) {
    const balances = {};
    fromSelect.querySelectorAll('option[data-balance]').forEach(opt => {
      balances[opt.value] = parseFloat(opt.dataset.balance);
    });

    const updateHint = () => {
      const val = fromSelect.value;
      if (val && balances[val] !== undefined) {
        balanceHint.textContent = `Solde disponible : ${balances[val].toLocaleString('fr-TN', {minimumFractionDigits:2})} DNT`;
        balanceHint.style.color = 'var(--teal)';
      } else {
        balanceHint.textContent = '';
      }
    };
    fromSelect.addEventListener('change', updateHint);
    updateHint();
  }

  // ── Amount warning ──
  if (amountInput && fromSelect && balanceHint) {
    const balances = {};
    fromSelect.querySelectorAll('option[data-balance]').forEach(opt => {
      balances[opt.value] = parseFloat(opt.dataset.balance);
    });

    amountInput.addEventListener('input', () => {
      const amount  = parseFloat(amountInput.value);
      const accId   = fromSelect.value;
      const balance = balances[accId];
      const warn    = document.getElementById('amountWarn');
      if (!warn) return;
      if (balance !== undefined && amount > balance) {
        warn.textContent = `⚠ Solde insuffisant (${balance.toLocaleString('fr-TN', {minimumFractionDigits:2})} DNT disponible)`;
        warn.style.color = 'var(--danger)';
        amountInput.style.borderColor = 'var(--danger)';
      } else {
        warn.textContent = '';
        amountInput.style.borderColor = '';
      }
    });
  }

  // ── Form validation before submit ──
  const transferForm = document.getElementById('transferForm');
  if (transferForm) {
    transferForm.addEventListener('submit', e => {
      const amount = parseFloat(amountInput?.value);
      if (!amount || amount <= 0) {
        e.preventDefault();
        showToast('Veuillez saisir un montant valide.', 'danger');
        return;
      }
      if (!toInput?.value.trim()) {
        e.preventDefault();
        showToast('Veuillez saisir un numéro de compte destinataire.', 'danger');
        return;
      }
      if (!fromSelect?.value) {
        e.preventDefault();
        showToast('Veuillez sélectionner un compte source.', 'danger');
        return;
      }
    });
  }
});
