async function pollStatus() {
  try {
    const res = await fetch('/api/status');
    if (!res.ok) return;
    const data = await res.json();
    const statusText = document.getElementById('status-text');
    const progressBar = document.getElementById('progress-bar');
    if (statusText) {
      statusText.textContent = `${data.state || 'idle'} - ${data.message || ''}`;
    }
    if (progressBar) {
      progressBar.style.width = `${data.progress || 0}%`;
    }
  } catch (_e) {
    // no-op
  }
}

setInterval(pollStatus, 3000);
pollStatus();

const checkNowBtn = document.getElementById('check-now-btn');
if (checkNowBtn) {
  checkNowBtn.addEventListener('click', async () => {
    await fetch('/api/channel/check-now', { method: 'POST' });
    pollStatus();
  });
}

const channelForm = document.getElementById('channel-form');
if (channelForm) {
  channelForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const formData = new FormData(channelForm);
    const payload = Object.fromEntries(formData.entries());
    const res = await fetch('/api/channel/save', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    const result = document.getElementById('channel-result');
    if (result) {
      result.textContent = data.success
        ? `Saved: ${data.channel.name} (${data.channel.channel_id})`
        : `Failed: ${data.message || 'Unknown error'}`;
    }
  });
}

const settingsForm = document.getElementById('settings-form');
if (settingsForm) {
  settingsForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const formData = new FormData(settingsForm);
    const payload = Object.fromEntries(formData.entries());
    const res = await fetch('/api/settings/save', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    alert(data.success ? 'Settings saved' : `Failed: ${data.message || 'Unknown error'}`);
  });
}

document.querySelectorAll('.delete-clip-btn').forEach((btn) => {
  btn.addEventListener('click', async () => {
    const clipPath = btn.dataset.path;
    const res = await fetch('/api/clips/delete', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ clip_path: clipPath }),
    });
    const data = await res.json();
    if (data.success) {
      btn.closest('.clip-card')?.remove();
    }
  });
});
