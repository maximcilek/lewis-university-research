from piper import PiperVoice
import wave
import re

voice = PiperVoice.load("voices/en_US-ryan-high.onnx")

text="""
Through Eddie Murphy’s humor and the film’s exaggerated reversals, Trading Places demonstrates that comedy can be one of the most effective ways to make difficult socioeconomic truths visible.
"""
sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()]

with wave.open("output27.wav", "wb") as wav_file:
    wav_file.setnchannels(1)
    wav_file.setsampwidth(2)
    wav_file.setframerate(voice.config.sample_rate)

    for sentence in sentences:
        for chunk in voice.synthesize(sentence):
            wav_file.writeframes(chunk.audio_int16_bytes)