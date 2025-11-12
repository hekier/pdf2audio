"""
Text-to-Speech engine using Piper TTS
"""

import re
import logging
import wave
from pathlib import Path
from typing import List, Generator, Optional
import io

try:
    from piper import PiperVoice
    PIPER_AVAILABLE = True
except ImportError:
    PIPER_AVAILABLE = False

import numpy as np

from config import (
    DEFAULT_VOICE_MODEL,
    DEFAULT_SPEECH_SPEED,
    MIN_SPEECH_SPEED,
    MAX_SPEECH_SPEED,
    MAX_CHUNK_LENGTH,
    MIN_CHUNK_LENGTH,
    SENTENCE_ENDINGS,
    TTS_SAMPLE_RATE,
)

logger = logging.getLogger(__name__)


class TTSEngine:
    """Text-to-Speech engine using Piper"""

    def __init__(self, voice_model_path: Optional[str] = None, speed: float = DEFAULT_SPEECH_SPEED):
        """
        Initialize TTS engine

        Args:
            voice_model_path: Path to Piper voice model (.onnx file)
            speed: Speech speed multiplier (0.5-2.0)
        """
        if not PIPER_AVAILABLE:
            raise ImportError("piper-tts is not installed. Install it with: pip install piper-tts")

        self.voice_model_path = Path(voice_model_path) if voice_model_path else DEFAULT_VOICE_MODEL

        if not self.voice_model_path.exists():
            raise FileNotFoundError(
                f"Voice model not found: {self.voice_model_path}\n"
                f"Download from: https://huggingface.co/rhasspy/piper-voices"
            )

        # Validate speed
        self.speed = max(MIN_SPEECH_SPEED, min(MAX_SPEECH_SPEED, speed))
        if self.speed != speed:
            logger.warning(f"Speed adjusted to {self.speed} (valid range: {MIN_SPEECH_SPEED}-{MAX_SPEECH_SPEED})")

        # Load voice model
        logger.info(f"Loading voice model: {self.voice_model_path}")
        self.voice = PiperVoice.load(str(self.voice_model_path))
        logger.info("Voice model loaded successfully")

        self.sample_rate = TTS_SAMPLE_RATE

    def text_to_chunks(self, text: str) -> List[str]:
        """
        Split text into optimal chunks for TTS processing

        Args:
            text: Input text

        Returns:
            List of text chunks
        """
        # Split by paragraphs first
        paragraphs = text.split('\n\n')
        chunks = []

        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue

            # If paragraph is small enough, use it as one chunk
            if len(paragraph) <= MAX_CHUNK_LENGTH:
                chunks.append(paragraph)
                continue

            # Split long paragraphs by sentences
            sentences = self._split_into_sentences(paragraph)

            current_chunk = ""
            for sentence in sentences:
                # If adding this sentence exceeds max length, save current chunk
                if len(current_chunk) + len(sentence) > MAX_CHUNK_LENGTH and len(current_chunk) >= MIN_CHUNK_LENGTH:
                    chunks.append(current_chunk.strip())
                    current_chunk = sentence
                else:
                    current_chunk += " " + sentence if current_chunk else sentence

            # Add remaining chunk
            if current_chunk.strip():
                chunks.append(current_chunk.strip())

        logger.info(f"Split text into {len(chunks)} chunks")
        return chunks

    @staticmethod
    def _split_into_sentences(text: str) -> List[str]:
        """
        Split text into sentences

        Args:
            text: Input text

        Returns:
            List of sentences
        """
        # Simple sentence splitting based on punctuation
        # This is a basic implementation - could be enhanced with NLP libraries
        pattern = r'([.!?]+[\s]+)'
        parts = re.split(pattern, text)

        sentences = []
        for i in range(0, len(parts) - 1, 2):
            sentence = parts[i] + (parts[i + 1] if i + 1 < len(parts) else '')
            sentences.append(sentence.strip())

        # Add any remaining text
        if len(parts) % 2 == 1 and parts[-1].strip():
            sentences.append(parts[-1].strip())

        return [s for s in sentences if s]

    def synthesize_chunk(self, text: str) -> bytes:
        """
        Synthesize a single text chunk to audio

        Args:
            text: Text to synthesize

        Returns:
            WAV audio data as bytes
        """
        # Piper synthesize returns generator of AudioChunk objects
        audio_data_parts = []

        for audio_chunk in self.voice.synthesize(text):
            # AudioChunk object has audio_int16_bytes property for direct bytes access
            if hasattr(audio_chunk, 'audio_int16_bytes'):
                audio_data_parts.append(audio_chunk.audio_int16_bytes)
            elif hasattr(audio_chunk, 'audio_int16_array'):
                # Fallback: get int16 array and convert to bytes
                audio_data_parts.append(audio_chunk.audio_int16_array.tobytes())
            elif isinstance(audio_chunk, bytes):
                # Fallback for older API that returned bytes directly
                audio_data_parts.append(audio_chunk)
            else:
                # Last resort: try to get as numpy array
                if isinstance(audio_chunk, np.ndarray):
                    audio_data_parts.append(audio_chunk.tobytes())
                else:
                    raise TypeError(f"Unexpected audio chunk type: {type(audio_chunk)}")

        # Combine all audio chunks
        audio_data = b''.join(audio_data_parts)

        # Convert to numpy array
        audio_array = np.frombuffer(audio_data, dtype=np.int16)

        # Apply speed adjustment if needed
        if self.speed != 1.0:
            audio_array = self._adjust_speed(audio_array, self.speed)

        # Convert back to WAV format
        wav_data = self._to_wav(audio_array)

        return wav_data

    @staticmethod
    def _adjust_speed(audio_array: np.ndarray, speed: float) -> np.ndarray:
        """
        Adjust audio playback speed

        Args:
            audio_array: Input audio as numpy array
            speed: Speed multiplier

        Returns:
            Speed-adjusted audio array
        """
        # Simple resampling for speed adjustment
        # For better quality, could use librosa or similar
        indices = np.arange(0, len(audio_array), speed)
        indices = indices[indices < len(audio_array)].astype(int)
        return audio_array[indices]

    def _to_wav(self, audio_array: np.ndarray) -> bytes:
        """
        Convert audio array to WAV format bytes

        Args:
            audio_array: Audio data as numpy array

        Returns:
            WAV file bytes
        """
        # Create WAV file in memory
        wav_buffer = io.BytesIO()

        with wave.open(wav_buffer, 'wb') as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(self.sample_rate)
            wav_file.writeframes(audio_array.tobytes())

        return wav_buffer.getvalue()

    def synthesize_text(self, text: str) -> Generator[bytes, None, None]:
        """
        Synthesize full text to audio chunks

        Args:
            text: Full text to synthesize

        Yields:
            WAV audio chunks
        """
        chunks = self.text_to_chunks(text)

        for i, chunk in enumerate(chunks):
            logger.info(f"Synthesizing chunk {i + 1}/{len(chunks)}")
            audio_chunk = self.synthesize_chunk(chunk)
            yield audio_chunk

    def synthesize_to_file(self, text: str, output_path: str) -> List[str]:
        """
        Synthesize text and save as temporary WAV chunks

        Args:
            text: Text to synthesize
            output_path: Base path for output files

        Returns:
            List of generated WAV file paths
        """
        output_path = Path(output_path)
        output_dir = output_path.parent
        output_dir.mkdir(parents=True, exist_ok=True)

        wav_files = []
        chunks = self.text_to_chunks(text)

        for i, chunk in enumerate(chunks):
            chunk_file = output_dir / f"{output_path.stem}_chunk_{i:04d}.wav"
            logger.info(f"Synthesizing chunk {i + 1}/{len(chunks)} to {chunk_file.name}")

            audio_data = self.synthesize_chunk(chunk)

            with open(chunk_file, 'wb') as f:
                f.write(audio_data)

            wav_files.append(str(chunk_file))

        logger.info(f"Generated {len(wav_files)} WAV chunks")
        return wav_files


def synthesize_text_to_audio(
    text: str,
    output_path: str,
    voice_model: Optional[str] = None,
    speed: float = DEFAULT_SPEECH_SPEED
) -> List[str]:
    """
    Convenience function to synthesize text to audio files

    Args:
        text: Text to synthesize
        output_path: Output file path
        voice_model: Path to voice model
        speed: Speech speed

    Returns:
        List of generated WAV file paths
    """
    engine = TTSEngine(voice_model, speed)
    return engine.synthesize_to_file(text, output_path)
