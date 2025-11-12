# PDF to Audio Converter - Proposed Solution

## Technology Stack Overview

### PDF Text Extraction Libraries

#### Option 1: PyMuPDF (fitz) - Recommended
- **Pros**: Fast, accurate, good layout handling, actively maintained
- **Cons**: Slightly larger dependency
- **Best for**: General-purpose PDF extraction with good quality

#### Option 2: pdfplumber
- **Pros**: Excellent for complex PDFs, tables, precise layout control
- **Cons**: Slower than PyMuPDF
- **Best for**: PDFs with complex layouts and tables

#### Option 3: PyPDF2
- **Pros**: Lightweight, simple API
- **Cons**: Less robust with complex PDFs
- **Best for**: Simple, well-formatted PDFs only

**Recommendation**: **PyMuPDF** for best balance of speed, accuracy, and ease of use.

### Layout Handling & Fallback Strategy
- Default to PyMuPDF for speed, but expose a `--layout-engine` CLI flag so users can switch to pdfplumber when dealing with multi-column or table-heavy PDFs.
- Implement extraction confidence heuristics (e.g., count of blank pages, abrupt drops in character counts, obvious column ordering issues); when triggered, warn the user and recommend rerunning with the alternate engine.
- Keep the extraction pipeline modular so new layout handlers can be plugged in without touching the rest of the flow.

### Text-to-Speech Engines

#### Option 1: Piper TTS - Recommended
- **Quality**: Very natural-sounding, neural voices
- **Performance**: Lightweight, fast processing
- **Resource Usage**: Low CPU/memory requirements
- **Voices**: Multiple high-quality voices in various languages
- **Local**: 100% local execution
- **Pros**: Best balance of quality, speed, and resource usage
- **Cons**: Requires downloading voice models (small files)

#### Option 2: Coqui TTS
- **Quality**: High-quality neural TTS, voice cloning capable
- **Performance**: Slower than Piper
- **Resource Usage**: Higher CPU/GPU requirements
- **Voices**: Many models including XTTS for voice cloning
- **Local**: Fully local
- **Pros**: More features, very natural output
- **Cons**: Heavier, slower processing

#### Option 3: pyttsx3
- **Quality**: Uses system TTS engines (robotic sounding)
- **Performance**: Very fast
- **Resource Usage**: Minimal
- **Pros**: Zero setup, works out of the box
- **Cons**: Not suitable for extended listening (unnatural voice)

**Recommendation**: **Piper TTS** for natural voice quality suitable for long listening sessions.

**Note on Ollama**: While Ollama is excellent for running LLMs locally, it's designed for text generation, not speech synthesis, and is not suitable for TTS tasks.

## Recommended Solution Architecture

### Component Design

```
┌─────────────────────────────────────────────────────┐
│                   CLI Interface                      │
│              (main.py - argparse)                    │
└──────────────────┬──────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────┐
│              PDF Text Extractor                      │
│         (pdf_extractor.py - PyMuPDF)                │
│  • Extract text from PDF                            │
│  • Clean and preprocess text                        │
│  • Handle page breaks and paragraphs                │
└──────────────────┬──────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────┐
│           Text-to-Speech Engine                      │
│          (tts_engine.py - Piper TTS)                │
│  • Load voice model                                 │
│  • Convert text to speech                           │
│  • Handle chunking for long texts                   │
└──────────────────┬──────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────┐
│              Audio Output Handler                    │
│         (audio_handler.py)                          │
│  • Combine audio chunks                             │
│  • Add chapter markers and metadata                 │
│  • Convert to M4B format via ffmpeg                 │
│  • Validate outputs and report paths                │
└─────────────────────────────────────────────────────┘
```

### Project Structure

```
pdf2audio/
├── main.py              # CLI entry point and argument parsing
├── pdf_extractor.py     # PDF text extraction logic
├── tts_engine.py        # TTS processing with Piper
├── audio_handler.py     # Audio chunk combining + M4B conversion with metadata
├── config.py            # Configuration and constants
├── requirements.txt     # Python dependencies
├── README.md            # Usage instructions
├── REQUIREMENTS.md      # Project requirements
├── SOLUTION.md          # This file
└── models/              # Directory for Piper voice models
    └── .gitkeep
```

### Core Dependencies

```
pymupdf>=1.23.0          # PDF parsing
pdfplumber               # Fallback PDF parser for complex layouts
piper-tts>=1.2.0         # Text-to-speech
numpy                    # Required by Piper
mutagen                  # Audio metadata handling for M4B
ffmpeg (system binary)   # Audio conversion to M4B format
```

### Optional Dependencies

```
rich                     # Progress / status output
ffmpeg-python            # Advanced audio processing utilities
```

## Implementation Flow

### 1. PDF Text Extraction
```python
1. Open PDF file with PyMuPDF
2. Iterate through pages
3. Extract text with layout preservation
4. Run extraction quality heuristics (blank pages, character counts, column detection)
5. If heuristics fail or user sets --layout-engine=pdfplumber, re-run extraction with pdfplumber
6. Clean text:
   - Remove excessive whitespace
   - Handle hyphenation
   - Preserve paragraph breaks
7. Return cleaned text string
```

### 2. Text Preprocessing
```python
1. Split text into manageable chunks at paragraph/sentence boundaries (keep chunks under Piper's optimal token length)
2. Insert explicit pause markers around paragraph breaks to drive pacing
3. Normalize special characters while preserving smart quotes and punctuation that influence prosody
4. Expand common abbreviations (e.g., "Dr.", "Fig.") to prevent awkward pauses
5. Handle numbers (years, ordinals) via simple verbalization helpers
```

### 3. Text-to-Speech Conversion
```python
1. Load Piper voice model (one-time per session)
2. Process text through TTS engine (entire document or single random page in test mode)
3. Generate audio chunks
4. Combine chunks into final audio stream
5. Convert to M4B format via ffmpeg with appropriate metadata (title, author, chapters)
6. Report output path and file information
```

### 4. CLI Interface
```bash
# Basic usage
python main.py input.pdf -o output.m4b

# With options
python main.py input.pdf -o output.m4b --voice en_US-amy-medium --speed 1.0

# Test with random page before full conversion
python main.py input.pdf --test-random-page -o test_sample.m4b

# Health check / dependency validation
python main.py --verify-environment
```

- Display progress (pages processed, TTS chunks generated) via `rich` progress bars.
- Fail fast with descriptive errors for missing voice models, absent ffmpeg binary, or unreadable PDFs and suggest remediation commands.
- Provide a dry-run/`--verify-environment` command that checks for dependencies and voice models before conversion starts.
- `--test-random-page` flag extracts and converts a single random page to verify extraction quality and voice output before processing entire document.

## Usability & Error Handling
- Centralized error handler categorizes failures (PDF read, extraction confidence, TTS, audio conversion) and returns clear exit codes plus remediation tips.
- Layout heuristics log warnings and optionally emit a JSON diagnostics report so users can inspect problematic pages.
- Progress events (pages processed, chunk percentage, final M4B conversion) are streamed to stdout and can be silenced with `--quiet`.

## Testing & Quality Assurance
- **Unit tests**: pdf_extractor parsing for single/multi-column samples, preprocessing rules (abbreviation expansion, sentence segmentation), audio handler M4B conversion stubs.
- **Integration tests**: deterministic fixture PDF converted end-to-end with a lightweight Piper voice; validate audio output integrity and ensure M4B generation with metadata succeeds.
- **Random page testing**: `--test-random-page` feature allows quick verification of extraction and voice quality before full conversion.
- **Golden samples**: store short reference M4B files to detect regressions in pauses, clipping, or metadata.
- **Tooling**: run formatting (`ruff`, `black`) and static checks in CI along with a smoke test that invokes `main.py --verify-environment`.

## Documentation Deliverables
- README sections for dependency setup (including ffmpeg instructions), CLI examples, and troubleshooting table.
- CONTRIBUTING guide covering testing workflow, adding new voices/layout handlers, and updating fixtures.
- Inline module docstrings describing extension points for new voice models or extraction engines.

## Configuration Options

### Voice Selection
- Default voice: `en_US-lessac-medium` (clear, neutral)
- Other options: Various Piper voices downloadable
- Configuration: Via command-line argument or config file

### Output Format
- M4B (MPEG-4 Audio Book format)
  - Supports chapter markers for multi-page documents
  - Includes metadata (title, author, description)
  - Optimized for audiobook players
  - AAC audio codec for efficient compression with high quality
  - Generated via ffmpeg with appropriate audiobook flags

### Processing Options
- Speech speed adjustment (0.5x to 2.0x)
- Output quality settings
- Chunk size for processing

## Performance Considerations

### Expected Performance
- **Text Extraction**: ~1-2 seconds per page
- **TTS Generation**: ~1-3x real-time (10 min text → 10-30 min processing)
- **Memory Usage**: ~500MB - 1GB depending on PDF size

### Optimization Strategies
- Process text in chunks to manage memory
- Cache voice model between conversions
- Optional: Progress bars for user feedback

## Future Enhancements (Post-MVP)

1. Batch processing of multiple PDFs
2. Resume from specific page/chapter
3. Multiple language support
4. Voice customization options
5. GUI wrapper
6. Streaming playback during generation
7. Smart chapter/section detection
8. Table of contents generation
