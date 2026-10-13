# Roadmap

[← Main README](../README.md) · See also: [Changelog](CHANGELOG.md) · [Project Overview](PROJECT_OVERVIEW.md)

Guiding rule: **extract completely first, then organise**. Raw OCR is the source; Smart OCR structures it; optional local AI polishes it without silently deleting OCR pairs.

| Area | Status |
|---|---|
| Smart / Raw / AI Smart OCR | ✅ implemented |
| Fast / Balanced / Deep accuracy | ✅ implemented |
| Complete-image OCR and grid/cell recovery | ✅ implemented |
| Dense-screenshot structural recovery | ✅ implemented |
| Unified single-image and batch OCR job path | ✅ implemented |
| Unlimited application OCR queue | ✅ implemented |
| Dynamic Tesseract language discovery and on-demand packs | ✅ implemented |
| Select Area: zoom / fit / pan / rotate / crop / multi-box | ✅ implemented |
| Rich editor + MD/TXT/HTML/DOCX/CSV export | ✅ implemented |
| Local Ollama AI + Local AI Agents | ✅ implemented |
| Portable Windows build + regression/smoke checks | ✅ implemented |
| Project save/open workflow | 📝 future enhancement |
| Dedicated vocabulary review / spaced repetition | 💡 future idea |
| Drag-and-drop file input | 💡 future idea |
| More OCR engines behind the existing engine interface | 💡 future idea |

## Future priorities

1. Improve correction/review workflows without changing the complete-OCR guarantee.
2. Expand language-management UX around installed Tesseract packs.
3. Add stronger project persistence for multi-session study work.
4. Keep the portable build small and auditable.

Feature selection is driven by one question: **does it help turn image-based language material into complete, reviewable study notes with less manual typing?**
