async function pollStatus() {
  try {
    const res = await fetch('/api/status');
    if (!res.ok) {
      const statusText = document.getElementById('status-text');
      if (statusText) {
        statusText.textContent = 'status unavailable';
      }
      return;
    }
    const data = await res.json();
    const statusText = document.getElementById('status-text');
    const progressBar = document.getElementById('progress-bar');
    if (statusText) {
      statusText.textContent = `${data.state || 'idle'} - ${data.message || ''}`;
    }
    if (progressBar) {
      progressBar.style.width = `${data.progress || 0}%`;
    }
  } catch (e) {
    console.error('Status polling failed', e);
  }
}

setInterval(pollStatus, 3000);
pollStatus();

const checkNowBtn = document.getElementById('check-now-btn');
if (checkNowBtn) {
  checkNowBtn.addEventListener('click', async () => {
    try {
      const res = await fetch('/api/channel/check-now', { method: 'POST' });
      const data = await res.json();
      const statusText = document.getElementById('status-text');
      if (statusText && !data.success) {
        statusText.textContent = data.message || 'Failed to start check';
      }
      pollStatus();
    } catch (e) {
      const statusText = document.getElementById('status-text');
      if (statusText) {
        statusText.textContent = 'Failed to start check';
      }
      console.error('Check-now request failed', e);
    }
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
    const messageEl = document.getElementById('settings-message');
    if (messageEl) {
      messageEl.textContent = data.success ? 'Settings saved' : `Failed: ${data.message || 'Unknown error'}`;
    }
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
