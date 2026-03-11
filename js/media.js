/**
 * QuoteKeeper — Media Detection Module
 * Detects currently playing media (podcast/audiobook) via MediaSession API
 * and provides audio recording capabilities.
 */

const MediaDetector = (() => {
  /**
   * Attempt to read the current media session metadata.
   * The MediaSession API exposes metadata set by the currently active
   * media app (podcast player, audiobook app, music player, etc.).
   */
  function getNowPlaying() {
    if ('mediaSession' in navigator && navigator.mediaSession.metadata) {
      const meta = navigator.mediaSession.metadata;
      return {
        title: meta.title || '',
        artist: meta.artist || '',
        album: meta.album || '',
        artwork: meta.artwork && meta.artwork.length > 0
          ? meta.artwork[meta.artwork.length - 1].src
          : null,
      };
    }
    return null;
  }

  /**
   * Poll for media metadata changes. Calls callback when new metadata is detected.
   * Returns a stop function.
   */
  function watchNowPlaying(callback, intervalMs = 2000) {
    let lastTitle = '';
    const id = setInterval(() => {
      const info = getNowPlaying();
      if (info && info.title !== lastTitle) {
        lastTitle = info.title;
        callback(info);
      }
    }, intervalMs);

    // Fire immediately
    const info = getNowPlaying();
    if (info) {
      lastTitle = info.title;
      callback(info);
    }

    return () => clearInterval(id);
  }

  return { getNowPlaying, watchNowPlaying };
})();


/**
 * AudioCapture — records audio from mic or system (where supported)
 * and can produce a blob URL for playback + speech-to-text.
 */
const AudioCapture = (() => {
  let mediaRecorder = null;
  let chunks = [];
  let timerInterval = null;
  let startTime = 0;

  async function startRecording(onTick) {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    chunks = [];
    mediaRecorder = new MediaRecorder(stream, { mimeType: getSupportedMimeType() });

    mediaRecorder.ondataavailable = (e) => {
      if (e.data.size > 0) chunks.push(e.data);
    };

    startTime = Date.now();
    if (onTick) {
      timerInterval = setInterval(() => {
        const elapsed = Math.floor((Date.now() - startTime) / 1000);
        onTick(formatTime(elapsed));
      }, 500);
    }

    mediaRecorder.start(500); // collect in 500ms chunks
  }

  function stopRecording() {
    return new Promise((resolve) => {
      if (!mediaRecorder || mediaRecorder.state === 'inactive') {
        resolve(null);
        return;
      }

      clearInterval(timerInterval);
      timerInterval = null;

      mediaRecorder.onstop = () => {
        const blob = new Blob(chunks, { type: mediaRecorder.mimeType });
        const url = URL.createObjectURL(blob);

        // Stop all tracks to release mic
        mediaRecorder.stream.getTracks().forEach(t => t.stop());

        resolve({ blob, url });
      };

      mediaRecorder.stop();
    });
  }

  function isRecording() {
    return mediaRecorder && mediaRecorder.state === 'recording';
  }

  function getSupportedMimeType() {
    const types = ['audio/webm;codecs=opus', 'audio/webm', 'audio/mp4', 'audio/ogg'];
    for (const type of types) {
      if (MediaRecorder.isTypeSupported(type)) return type;
    }
    return 'audio/webm';
  }

  function formatTime(secs) {
    const m = String(Math.floor(secs / 60)).padStart(2, '0');
    const s = String(secs % 60).padStart(2, '0');
    return `${m}:${s}`;
  }

  return { startRecording, stopRecording, isRecording };
})();
