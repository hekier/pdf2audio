#!/usr/bin/env python3
"""Debug script to understand Piper AudioChunk structure"""

from piper import PiperVoice
from pathlib import Path

voice_model = Path("models/en_US-lessac-medium.onnx")
voice = PiperVoice.load(str(voice_model))

test_text = "Hello world, this is a test."

print("Synthesizing test text...")
for i, chunk in enumerate(voice.synthesize(test_text)):
    print(f"\nChunk {i}:")
    print(f"  Type: {type(chunk)}")
    print(f"  Dir: {[attr for attr in dir(chunk) if not attr.startswith('_')]}")

    # Try to find the actual data
    if hasattr(chunk, '__dict__'):
        print(f"  __dict__: {chunk.__dict__}")

    # Try common attributes
    for attr in ['pcm', 'audio', 'data', 'samples']:
        if hasattr(chunk, attr):
            val = getattr(chunk, attr)
            print(f"  {attr}: type={type(val)}, len={len(val) if hasattr(val, '__len__') else 'N/A'}")

    if i >= 2:  # Only check first few chunks
        break

print("\nDone!")
