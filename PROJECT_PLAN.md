# PDF to Audio Converter - Project Plan

## Project Timeline & Milestones

### Phase 1: Setup & Foundation (Step 1-2)
**Goal**: Set up project structure and core dependencies

#### Step 1: Project Initialization
- [x] Create project directory structure
- [x] Document requirements (REQUIREMENTS.md)
- [x] Document proposed solution (SOLUTION.md)
- [ ] Create requirements.txt
- [ ] Create basic README.md with setup instructions

#### Step 2: Environment Setup
- [ ] Set up Python virtual environment
- [ ] Install core dependencies (PyMuPDF, Piper TTS)
- [ ] Download and test a voice model
- [ ] Verify all dependencies work correctly

### Phase 2: Core Functionality (Step 3-5)
**Goal**: Implement basic PDF to audio conversion

#### Step 3: PDF Text Extraction Module
- [ ] Create pdf_extractor.py
- [ ] Implement PDF text extraction with PyMuPDF
- [ ] Add text cleaning and preprocessing that preserves sentence/paragraph boundaries
- [ ] Handle multi-page documents
- [ ] Implement extraction confidence heuristics and warnings
- [ ] Support alternate extraction engine (pdfplumber) behind CLI flag
- [ ] Test with sample PDFs covering single- and multi-column layouts

#### Step 4: TTS Engine Integration
- [ ] Create tts_engine.py
- [ ] Integrate Piper TTS library
- [ ] Implement voice model loading
- [ ] Implement text-to-speech conversion
- [ ] Handle long text chunking
- [ ] Test audio generation quality

#### Step 5: Audio Output Handler
- [ ] Create audio_handler.py for audio chunk combining
- [ ] Integrate ffmpeg for M4B conversion with chapter markers and metadata
- [ ] Add dependency validation for ffmpeg before runtime
- [ ] Test M4B generation quality, metadata, and chapter markers

### Phase 3: CLI Interface (Step 6)
**Goal**: Create user-friendly command-line interface

#### Step 6: Command-Line Interface
- [ ] Create main.py
- [ ] Implement argument parsing (argparse)
- [ ] Add input validation
- [ ] Implement error handling
- [ ] Add progress indicators
- [ ] Provide `--verify-environment` / dry-run dependency check
- [ ] Implement `--test-random-page` feature for quick verification
- [ ] Surface extractor confidence warnings and fallback suggestions to users
- [ ] Create help documentation

### Phase 4: Testing & Refinement (Step 7-8)
**Goal**: Ensure reliability and usability

#### Step 7: Testing
- [ ] Test with various PDF formats
- [ ] Test with different document lengths
- [ ] Test edge cases (empty PDFs, scanned images, etc.)
- [ ] Test `--test-random-page` feature with multiple PDFs
- [ ] Performance testing
- [ ] Error handling verification
- [ ] Add automated unit tests for extraction, preprocessing, and audio conversion
- [ ] Create golden-sample integration tests (M4B with metadata) for regression detection
- [ ] Verify M4B chapter markers and metadata accuracy

#### Step 8: Documentation & Polish
- [ ] Complete README.md with usage examples
- [ ] Add inline code documentation
- [ ] Create usage examples including `--test-random-page`
- [ ] Document known limitations
- [ ] Add troubleshooting guide
- [ ] Document ffmpeg installation and offline voice/model setup
- [ ] Explain extraction confidence warnings and how to switch layout engines
- [ ] Document M4B metadata and chapter marker functionality

### Phase 5: Optional Enhancements (Step 9)
**Goal**: Add nice-to-have features

#### Step 9: Additional Features (Optional)
- [ ] Speech speed control
- [ ] Multiple voice model presets and quick switching
- [ ] Configuration file support
- [ ] Enhanced telemetry (ETA, chapter markers, resume)
- [ ] Batch processing of multiple PDFs

## Implementation Checklist

### Critical Path (MVP)
```
1. ✅ Project structure and planning
2. ⬜ Install PyMuPDF + pdfplumber and validate extraction heuristics
3. ⬜ Install Piper TTS + ffmpeg and test M4B generation
4. ⬜ Implement pdf_extractor.py with preprocessing + fallback support
5. ⬜ Implement tts_engine.py and audio_handler.py (M4B with metadata)
6. ⬜ Implement main.py CLI with progress, dry-run, and test-random-page features
7. ⬜ End-to-end + golden audio testing with M4B validation
8. ⬜ Documentation & troubleshooting updates
```

### Nice-to-Have Features
```
⬜ Speech speed adjustment
⬜ Voice selection CLI option
⬜ Config file support
⬜ Batch processing
⬜ Resume/playback bookmarks
⬜ Streaming or live playback
```

## Decision Points

### Before Implementation Starts

**Decision 1: TTS Engine**
- [ ] Confirm Piper TTS as the choice
- [ ] Alternative: Coqui TTS if more features needed
- [ ] Decision: _______________

**Decision 2: Voice Model**
- [ ] Select default English voice model
- [ ] Options: en_US-lessac-medium, en_US-amy-medium, etc.
- [ ] Decision: _______________

**Decision 3: Output Format**
- [x] M4B (MPEG-4 Audio Book) format only
- [x] Includes chapter markers and metadata support
- [x] Decision: M4B only (audiobook-optimized format with metadata)

**Decision 4: Additional Features**
- [ ] Which optional features to include after MVP?
- [ ] Speech speed control? (yes/no)
- [ ] Multiple voice support beyond default? (yes/no)
- [x] Progress indicators + dependency checks (required for MVP)
- [x] Random page test/verification mode (required for MVP)
- [ ] Decisions: _______________

## Risk Assessment

### Technical Risks

**Risk 1: PDF Text Extraction Quality**
- **Impact**: Medium
- **Likelihood**: Low
- **Mitigation**: Use PyMuPDF (proven library), test with various PDFs

**Risk 2: TTS Voice Quality**
- **Impact**: High
- **Likelihood**: Low
- **Mitigation**: Piper TTS has good reviews, can test before full implementation

**Risk 3: Performance Issues**
- **Impact**: Medium
- **Likelihood**: Medium
- **Mitigation**: Implement chunking, optimize processing, add progress indicators

**Risk 4: Dependency Installation Issues**
- **Impact**: Medium
- **Likelihood**: Medium
- **Mitigation**: Clear installation instructions, test on fresh environment

**Risk 5: M4B Conversion and Metadata Handling**
- **Impact**: Medium
- **Likelihood**: Low
- **Mitigation**: Use ffmpeg with well-tested flags, validate output with mutagen, test chapter markers thoroughly

## Success Criteria

### Minimum Viable Product (MVP)
- [ ] Successfully extracts text from standard PDFs
- [ ] Generates natural-sounding M4B audio files with metadata
- [ ] Simple CLI interface works correctly
- [ ] Runs entirely locally without internet
- [ ] Audio quality suitable for extended listening
- [ ] Test-random-page feature works for quick verification
- [ ] Basic error handling and user feedback

### Quality Metrics
- **Text Extraction Accuracy**: >95% for standard PDFs
- **Audio Quality**: Natural sounding, clear pronunciation
- **Performance**: Process at reasonable speed (1-3x real-time)
- **Reliability**: Handles errors gracefully without crashes
- **Usability**: Single command to convert PDF to audio

## Next Steps

1. **Await user confirmation** on technology choices
2. **Create requirements.txt** with dependencies
3. **Set up development environment**
4. **Begin Phase 2** implementation (PDF extraction)
5. **Iterate based on testing results**

## Notes

- Keep code modular for easy maintenance and testing
- Focus on MVP first, enhancements later
- Document as we go to save time later
- Test incrementally at each step
