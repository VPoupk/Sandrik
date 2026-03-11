/**
 * QuoteKeeper — Voice / Speech-to-Text Module
 * Uses Web Speech API for live dictation and audio transcription.
 */

const VoiceInput = (() => {
  let recognition = null;
  let isListening = false;

  function isSupported() {
    return 'webkitSpeechRecognition' in window || 'SpeechRecognition' in window;
  }

  /**
   * Start live speech recognition (dictation mode).
   * @param {Object} opts
   * @param {function} opts.onResult - called with (transcript, isFinal)
   * @param {function} opts.onEnd - called when recognition ends
   * @param {function} opts.onError - called on error
   * @param {string} opts.lang - language code, default 'en-US'
   */
  function startDictation({ onResult, onEnd, onError, lang = 'en-US' }) {
    if (!isSupported()) {
      onError?.('Speech recognition is not supported in this browser.');
      return;
    }

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = lang;

    recognition.onresult = (event) => {
      let interimTranscript = '';
      let finalTranscript = '';

      for (let i = event.resultIndex; i < event.results.length; i++) {
        const transcript = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          finalTranscript += transcript;
        } else {
          interimTranscript += transcript;
        }
      }

      if (finalTranscript) {
        onResult?.(finalTranscript, true);
      } else if (interimTranscript) {
        onResult?.(interimTranscript, false);
      }
    };

    recognition.onerror = (event) => {
      if (event.error !== 'aborted') {
        onError?.(event.error);
      }
    };

    recognition.onend = () => {
      isListening = false;
      onEnd?.();
    };

    recognition.start();
    isListening = true;
  }

  function stopDictation() {
    if (recognition) {
      recognition.stop();
      recognition = null;
      isListening = false;
    }
  }

  function getIsListening() {
    return isListening;
  }

  /**
   * Transcribe an audio blob using Web Speech API by playing it back.
   * NOTE: On mobile browsers, the Web Speech API only captures mic input,
   * so for recorded audio clips we provide the blob URL for manual playback
   * and the user can dictate over it or manually transcribe.
   * In environments that support it, we attempt direct recognition.
   */
  function transcribeBlob(blob) {
    // The Web Speech API doesn't support transcribing audio files directly.
    // We return the blob URL so the user can listen and type/dictate the text.
    return Promise.resolve({
      supported: false,
      message: 'Play the recording and use Dictate to transcribe, or type it manually.',
      blobUrl: URL.createObjectURL(blob),
    });
  }

  return { isSupported, startDictation, stopDictation, getIsListening, transcribeBlob };
})();
