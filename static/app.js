const form = document.getElementById('crawl-form');
const progress = document.getElementById('progress-bar');
const bar = progress.querySelector('.bar-fill');
const linkContainer = document.getElementById('download-link');
const messages = document.getElementById('messages');
let interval;

function showMessage(text, type = 'info') {
  messages.innerHTML = `<div class="message ${type}">${text}</div>`;
}

form.addEventListener('submit', function(e) {
  e.preventDefault();
  messages.innerHTML = '';
  linkContainer.innerHTML = '';
  bar.style.width = '0%';
  progress.classList.remove('hidden');

  fetch('/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url: form.url.value })
  })
  .then(res => res.json())
  .then(data => {
    if (data.error) {
      progress.classList.add('hidden');
      showMessage(data.error, 'error');
    } else {
      startPolling(data.download_url);
    }
  })
  .catch(() => {
    progress.classList.add('hidden');
    showMessage('Unexpected error occurred.', 'error');
  });
});

function startPolling(url) {
  const maxDuration = 60 * 1000; // 60 seconds timeout
  const startTime = Date.now();
  interval = setInterval(() => {
    const elapsed = Date.now() - startTime;
    if (elapsed > maxDuration) {
      clearInterval(interval);
      progress.classList.add('hidden');
      showMessage('Operation timed out after 60 seconds.', 'error');
      return;
    }
    const percent = Math.min((elapsed / maxDuration) * 90, 90);
    bar.style.width = percent + '%';
  }, 1000);

  const check = () => {
    fetch('/status')
      .then(res => res.json())
      .then(status => {
        if (status.ready) {
          clearInterval(interval);
          bar.style.width = '100%';
          showDownload(url);
        } else {
          setTimeout(check, 1000);
        }
      })
      .catch(() => {
        clearInterval(interval);
        progress.classList.add('hidden');
        showMessage('Error checking status.', 'error');
      });
  };
  check();
}

function showDownload(url) {
  progress.classList.add('hidden');
  linkContainer.innerHTML = `
    <a href="${url}" class="button">Download ZIP</a>
    <span id="remove-zip" class="remove-zip">&times;</span>
  `;
  document.getElementById('remove-zip').addEventListener('click', () => {
    fetch(url, { method: 'DELETE' }).then(() => {
      linkContainer.innerHTML = '';
      showMessage('Archive removed.', 'info');
    });
  });
}