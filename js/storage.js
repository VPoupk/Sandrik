/**
 * QuoteKeeper — Local Storage Module
 * Persists quotes to localStorage with IndexedDB-like structure.
 */

const QuoteStore = (() => {
  const STORAGE_KEY = 'quotekeeper_quotes';

  function generateId() {
    return Date.now().toString(36) + Math.random().toString(36).slice(2, 8);
  }

  function getAll() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      return raw ? JSON.parse(raw) : [];
    } catch {
      return [];
    }
  }

  function saveAll(quotes) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(quotes));
  }

  function getById(id) {
    return getAll().find(q => q.id === id) || null;
  }

  function create(data) {
    const quotes = getAll();
    const now = new Date().toISOString();
    const quote = {
      id: generateId(),
      text: data.text || '',
      source: {
        title: data.source?.title || '',
        artist: data.source?.artist || '',
        album: data.source?.album || '',
        url: data.source?.url || '',
      },
      tags: data.tags || [],
      audioClipUrl: data.audioClipUrl || null,
      createdAt: now,
      updatedAt: now,
    };
    quotes.unshift(quote);
    saveAll(quotes);
    return quote;
  }

  function update(id, data) {
    const quotes = getAll();
    const idx = quotes.findIndex(q => q.id === id);
    if (idx === -1) return null;

    quotes[idx] = {
      ...quotes[idx],
      ...data,
      updatedAt: new Date().toISOString(),
    };
    saveAll(quotes);
    return quotes[idx];
  }

  function remove(id) {
    const quotes = getAll().filter(q => q.id !== id);
    saveAll(quotes);
  }

  function search(query) {
    const q = query.toLowerCase().trim();
    if (!q) return getAll();
    return getAll().filter(quote => {
      return (
        quote.text.toLowerCase().includes(q) ||
        quote.source.title.toLowerCase().includes(q) ||
        quote.source.artist.toLowerCase().includes(q) ||
        quote.source.album.toLowerCase().includes(q) ||
        quote.tags.some(t => t.toLowerCase().includes(q))
      );
    });
  }

  return { getAll, getById, create, update, remove, search };
})();
