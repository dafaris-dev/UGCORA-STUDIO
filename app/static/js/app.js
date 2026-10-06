// UGCORA Studio - shared frontend helpers
async function submitForm(e, form, redirect, method, asForm) {
  e.preventDefault();
  const fd = new FormData(form);
  const opts = { method: method || 'POST' };
  if (asForm) {
    opts.body = fd;
  } else {
    opts.body = fd;
  }
  const resp = await fetch(form.action, opts);
  if (!resp.ok) {
    let msg = 'Request failed';
    try { const d = await resp.json(); msg = d.detail || msg; } catch (_) {}
    alert(msg);
    return false;
  }
  if (redirect) {
    const data = await resp.json().catch(() => ({}));
    if (data.id && redirect.indexOf('/products') === 0) {
      window.location = `/products/${data.id}`;
    } else {
      window.location = redirect;
    }
  } else {
    window.location.reload();
  }
  return false;
}
