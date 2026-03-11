/**
 * QuoteKeeper — Main Application Controller
 */

(() => {
  // ===== DOM REFERENCES =====
  const viewList = document.getElementById('view-list');
  const viewEditor = document.getElementById('view-editor');
  const quotesList = document.getElementById('quotes-list');
  const emptyState = document.getElementById('empty-state');
  const searchBar = document.getElementById('search-bar');
  const searchInput = document.getElementById('search-input');

  const btnNew = document.getElementById('btn-new');
  const btnSearch = document.getElementById('btn-search');
  const btnBack = document.getElementById('btn-back');
  const btnDelete = document.getElementById('btn-delete');

  const quoteText = document.getElementById('quote-text');
  const sourceTitle = document.getElementById('source-title');
  const sourceArtist = document.getElementById('source-artist');
  const sourceAlbum = document.getElementById('source-album');
  const btnRefreshSource = document.getElementById('btn-refresh-source');

  const btnVoice = document.getElementById('btn-voice');
  const btnRecordAudio = document.getElementById('btn-record-audio');
  const btnManualSource = document.getElementById('btn-manual-source');

  const voiceIndicator = document.getElementById('voice-indicator');
  const voiceStatus = document.getElementById('voice-status');
  const btnStopVoice = document.getElementById('btn-stop-voice');

  const audioIndicator = document.getElementById('audio-indicator');
  const audioTimer = document.getElementById('audio-timer');
  const btnStopAudio = document.getElementById('btn-stop-audio');

  const tagInput = document.getElementById('tag-input');
  const tagsList = document.getElementById('tags-list');
  const quoteTimestamp = document.getElementById('quote-timestamp');

  // Modal
  const modalSource = document.getElementById('modal-source');
  const modalSourceTitle = document.getElementById('modal-source-title');
  const modalSourceArtist = document.getElementById('modal-source-artist');
  const modalSourceAlbum = document.getElementById('modal-source-album');
  const modalSourceUrl = document.getElementById('modal-source-url');
  const modalCancel = document.getElementById('modal-cancel');
  const modalSave = document.getElementById('modal-save');

  // ===== STATE =====
  let currentQuoteId = null;
  let currentTags = [];
  let currentSource = { title: '', artist: '', album: '', url: '' };
  let currentAudioClipUrl = null;
  let stopMediaWatch = null;
  let autoSaveTimer = null;

  // ===== INIT =====
  function init() {
    renderList();
    bindEvents();

    // Start watching for now-playing media
    stopMediaWatch = MediaDetector.watchNowPlaying((info) => {
      // Only auto-update if we're in the editor and source is still default
      if (viewEditor.classList.contains('active') && !currentSource.title) {
        setSource(info);
      }
    });
  }

  // ===== LIST VIEW =====
  function renderList(filter) {
    const quotes = filter ? QuoteStore.search(filter) : QuoteStore.getAll();

    if (quotes.length === 0) {
      emptyState.style.display = '';
      // Remove all cards
      quotesList.querySelectorAll('.quote-card').forEach(el => el.remove());
      return;
    }

    emptyState.style.display = 'none';

    // Build HTML
    const fragment = document.createDocumentFragment();
    quotes.forEach(q => {
      const card = document.createElement('div');
      card.className = 'quote-card';
      card.dataset.id = q.id;

      const previewText = q.text || '(empty quote)';
      const sourceLine = q.source.title
        ? [q.source.title, q.source.artist].filter(Boolean).join(' — ')
        : '';
      const dateStr = formatDate(q.createdAt);

      card.innerHTML = `
        <div class="quote-card-text">${escapeHtml(previewText)}</div>
        <div class="quote-card-meta">
          ${sourceLine ? `
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/></svg>
            <span class="quote-card-source">${escapeHtml(sourceLine)}</span>
          ` : ''}
          <span class="quote-card-date">${dateStr}</span>
        </div>
        ${q.tags.length ? `
          <div class="quote-card-tags">
            ${q.tags.map(t => `<span class="tag">${escapeHtml(t)}</span>`).join('')}
          </div>
        ` : ''}
      `;

      card.addEventListener('click', () => openEditor(q.id));
      fragment.appendChild(card);
    });

    // Replace content
    quotesList.querySelectorAll('.quote-card').forEach(el => el.remove());
    quotesList.insertBefore(fragment, emptyState);
  }

  // ===== EDITOR VIEW =====
  function openEditor(id) {
    if (id) {
      const q = QuoteStore.getById(id);
      if (!q) return;
      currentQuoteId = q.id;
      quoteText.value = q.text;
      currentTags = [...q.tags];
      currentSource = { ...q.source };
      currentAudioClipUrl = q.audioClipUrl;
      quoteTimestamp.textContent = `Created ${formatDateFull(q.createdAt)} · Edited ${formatDateFull(q.updatedAt)}`;
    } else {
      // New quote — auto-detect source
      const nowPlaying = MediaDetector.getNowPlaying();
      currentQuoteId = null;
      quoteText.value = '';
      currentTags = [];
      currentSource = nowPlaying
        ? { title: nowPlaying.title, artist: nowPlaying.artist, album: nowPlaying.album, url: '' }
        : { title: '', artist: '', album: '', url: '' };
      currentAudioClipUrl = null;
      quoteTimestamp.textContent = '';
    }

    updateSourceBanner();
    renderTags();
    showView('editor');
    quoteText.focus();
    startAutoSave();
  }

  function closeEditor() {
    saveCurrentQuote();
    stopAutoSave();
    showView('list');
    renderList(searchInput.value);
  }

  function saveCurrentQuote() {
    const text = quoteText.value.trim();
    // Don't save completely empty quotes
    if (!text && !currentQuoteId) return;

    const data = {
      text,
      source: { ...currentSource },
      tags: [...currentTags],
      audioClipUrl: currentAudioClipUrl,
    };

    if (currentQuoteId) {
      QuoteStore.update(currentQuoteId, data);
    } else if (text) {
      const q = QuoteStore.create(data);
      currentQuoteId = q.id;
    }
  }

  function deleteCurrentQuote() {
    if (!currentQuoteId) {
      closeEditor();
      return;
    }
    if (confirm('Delete this quote?')) {
      QuoteStore.remove(currentQuoteId);
      currentQuoteId = null;
      stopAutoSave();
      showView('list');
      renderList();
    }
  }

  function startAutoSave() {
    stopAutoSave();
    autoSaveTimer = setInterval(() => saveCurrentQuote(), 3000);
  }

  function stopAutoSave() {
    if (autoSaveTimer) {
      clearInterval(autoSaveTimer);
      autoSaveTimer = null;
    }
  }

  // ===== SOURCE =====
  function setSource(info) {
    currentSource.title = info.title || '';
    currentSource.artist = info.artist || '';
    currentSource.album = info.album || '';
    updateSourceBanner();
  }

  function updateSourceBanner() {
    sourceTitle.textContent = currentSource.title || 'No media detected';
    sourceArtist.textContent = currentSource.artist || '';
    sourceAlbum.textContent = currentSource.album || '';

    sourceArtist.style.display = currentSource.artist ? '' : 'none';
    sourceAlbum.style.display = currentSource.album ? '' : 'none';
  }

  function refreshSource() {
    const info = MediaDetector.getNowPlaying();
    if (info) {
      setSource(info);
    } else {
      sourceTitle.textContent = 'No media detected — tap Edit Source';
    }
  }

  function openSourceModal() {
    modalSourceTitle.value = currentSource.title;
    modalSourceArtist.value = currentSource.artist;
    modalSourceAlbum.value = currentSource.album;
    modalSourceUrl.value = currentSource.url || '';
    modalSource.classList.remove('hidden');
  }

  function closeSourceModal() {
    modalSource.classList.add('hidden');
  }

  function saveSourceFromModal() {
    currentSource.title = modalSourceTitle.value.trim();
    currentSource.artist = modalSourceArtist.value.trim();
    currentSource.album = modalSourceAlbum.value.trim();
    currentSource.url = modalSourceUrl.value.trim();
    updateSourceBanner();
    closeSourceModal();
  }

  // ===== TAGS =====
  function renderTags() {
    tagsList.innerHTML = currentTags.map(t =>
      `<span class="tag" data-tag="${escapeHtml(t)}">${escapeHtml(t)}</span>`
    ).join('');
  }

  function addTag(text) {
    const tag = text.trim().toLowerCase();
    if (tag && !currentTags.includes(tag)) {
      currentTags.push(tag);
      renderTags();
    }
  }

  function removeTag(text) {
    currentTags = currentTags.filter(t => t !== text);
    renderTags();
  }

  // ===== VOICE DICTATION =====
  function startDictation() {
    if (!VoiceInput.isSupported()) {
      alert('Speech recognition is not supported in this browser. Try Chrome or Safari.');
      return;
    }

    btnVoice.classList.add('active');
    voiceIndicator.classList.remove('hidden');
    voiceStatus.textContent = 'Listening...';

    const cursorPos = quoteText.selectionStart;

    VoiceInput.startDictation({
      onResult: (transcript, isFinal) => {
        if (isFinal) {
          // Insert at cursor position
          const before = quoteText.value.slice(0, cursorPos);
          const after = quoteText.value.slice(cursorPos);
          const spaceBefore = before && !before.endsWith(' ') && !before.endsWith('\n') ? ' ' : '';
          quoteText.value = before + spaceBefore + transcript + after;
          voiceStatus.textContent = 'Listening...';
        } else {
          voiceStatus.textContent = transcript;
        }
      },
      onEnd: () => {
        btnVoice.classList.remove('active');
        voiceIndicator.classList.add('hidden');
      },
      onError: (err) => {
        voiceStatus.textContent = `Error: ${err}`;
        setTimeout(() => {
          btnVoice.classList.remove('active');
          voiceIndicator.classList.add('hidden');
        }, 2000);
      }
    });
  }

  function stopDictation() {
    VoiceInput.stopDictation();
  }

  // ===== AUDIO RECORDING =====
  async function startAudioRecording() {
    try {
      btnRecordAudio.classList.add('active');
      audioIndicator.classList.remove('hidden');
      audioTimer.textContent = '00:00';

      await AudioCapture.startRecording((time) => {
        audioTimer.textContent = time;
      });
    } catch (err) {
      alert('Could not access microphone. Please grant permission and try again.');
      btnRecordAudio.classList.remove('active');
      audioIndicator.classList.add('hidden');
    }
  }

  async function stopAudioRecording() {
    const result = await AudioCapture.stopRecording();
    btnRecordAudio.classList.remove('active');
    audioIndicator.classList.add('hidden');

    if (result) {
      currentAudioClipUrl = result.url;

      // Try to transcribe — if not supported, show playback option
      const transcription = await VoiceInput.transcribeBlob(result.blob);
      if (!transcription.supported) {
        // Add a playback link and prompt to dictate
        const note = '\n\n[Audio clip recorded — use Dictate to transcribe or type below]\n';
        quoteText.value += note;
        quoteText.focus();
      }
    }
  }

  // ===== VIEW MANAGEMENT =====
  function showView(name) {
    viewList.classList.remove('active');
    viewEditor.classList.remove('active');
    if (name === 'list') viewList.classList.add('active');
    if (name === 'editor') viewEditor.classList.add('active');
  }

  // ===== EVENT BINDINGS =====
  function bindEvents() {
    btnNew.addEventListener('click', () => openEditor(null));
    btnBack.addEventListener('click', closeEditor);
    btnDelete.addEventListener('click', deleteCurrentQuote);

    // Search
    btnSearch.addEventListener('click', () => {
      searchBar.classList.toggle('hidden');
      if (!searchBar.classList.contains('hidden')) {
        searchInput.focus();
      } else {
        searchInput.value = '';
        renderList();
      }
    });

    searchInput.addEventListener('input', () => {
      renderList(searchInput.value);
    });

    // Source
    btnRefreshSource.addEventListener('click', refreshSource);
    btnManualSource.addEventListener('click', openSourceModal);
    modalCancel.addEventListener('click', closeSourceModal);
    modalSave.addEventListener('click', saveSourceFromModal);

    // Close modal on backdrop click
    modalSource.addEventListener('click', (e) => {
      if (e.target === modalSource) closeSourceModal();
    });

    // Voice
    btnVoice.addEventListener('click', () => {
      if (VoiceInput.getIsListening()) {
        stopDictation();
      } else {
        startDictation();
      }
    });
    btnStopVoice.addEventListener('click', stopDictation);

    // Audio recording
    btnRecordAudio.addEventListener('click', () => {
      if (AudioCapture.isRecording()) {
        stopAudioRecording();
      } else {
        startAudioRecording();
      }
    });
    btnStopAudio.addEventListener('click', stopAudioRecording);

    // Tags
    tagInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ',') {
        e.preventDefault();
        addTag(tagInput.value.replace(',', ''));
        tagInput.value = '';
      }
    });

    tagsList.addEventListener('click', (e) => {
      const tagEl = e.target.closest('.tag');
      if (tagEl) removeTag(tagEl.dataset.tag);
    });

    // Auto-save on text change
    quoteText.addEventListener('input', () => {
      // Reset auto-save timer on each edit
      startAutoSave();
    });

    // Handle back gesture / hardware back
    window.addEventListener('popstate', () => {
      if (viewEditor.classList.contains('active')) {
        closeEditor();
      }
    });
  }

  // ===== UTILITIES =====
  function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  function formatDate(iso) {
    const d = new Date(iso);
    const now = new Date();
    const diffMs = now - d;
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffDays === 0) {
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } else if (diffDays === 1) {
      return 'Yesterday';
    } else if (diffDays < 7) {
      return d.toLocaleDateString([], { weekday: 'short' });
    } else {
      return d.toLocaleDateString([], { month: 'short', day: 'numeric' });
    }
  }

  function formatDateFull(iso) {
    return new Date(iso).toLocaleString([], {
      month: 'short', day: 'numeric', year: 'numeric',
      hour: '2-digit', minute: '2-digit'
    });
  }

  // ===== START =====
  init();
})();
