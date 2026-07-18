# Supported audio

FFmpeg/FFprobe support MP3, M4A/AAC, WAV, FLAC, OGG/OPUS, and audio streams in MP4, MOV, MKV, and WebM. Exactly one decodable file is accepted by the public notebook. Filenames may contain spaces and Unicode.

Compressed MP3 or M4A/AAC usually uploads faster than WAV. Compression is a transfer-size choice, not an accuracy improvement. The selected audio stream is decoded deterministically to mono 16 kHz float WAV; channel selection can be configured locally.
