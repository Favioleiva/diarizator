# Diarizator

[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Favioleiva/diarizator/blob/main/notebooks/Diarizator_Community1_Colab.ipynb)
[![Tests](https://github.com/Favioleiva/diarizator/actions/workflows/tests.yml/badge.svg)](https://github.com/Favioleiva/diarizator/actions/workflows/tests.yml)

Diarizator combines faster-whisper transcription with pyannote Community-1 speaker diarization and exports reproducible, privacy-conscious result bundles.

## Colab quick start

1. Accept the conditions on the [Community-1 model page](https://huggingface.co/pyannote/speaker-diarization-community-1), create a Hugging Face token, and add it to Colab Secrets as `HF_TOKEN` with notebook access enabled.
2. Open the badge above, choose a GPU runtime, and select **Run all**.
3. Upload one audio file and download the sanitized ZIP when processing finishes.

Google Drive is not required. Never paste a token into a notebook cell.

## Features and architecture

The pipeline validates media with FFprobe, decodes one canonical mono 16 kHz WAV using FFmpeg, performs ASR with faster-whisper, performs normal and exclusive diarization with Community-1, attributes words, groups speaker turns, validates every result, and creates a sanitized ZIP. Checkpoints support safe retry; GPU selection and bounded out-of-memory fallback are recorded.

Supported formats include MP3, M4A/AAC, WAV, FLAC, OGG/OPUS, and audio tracks from common MP4, MOV, MKV, and WebM files. For faster browser uploads, a compressed format such as MP3 is recommended. M4A/AAC is also compact. WAV files are usually much larger. MP3 does not improve diarization accuracy.

## Python API

```python
from diarizator import Diarizator, DiarizatorConfig

pipeline = Diarizator(DiarizatorConfig(backend="community-1", speaker_count_mode="estimated"))
result_dir = pipeline.run("conversation.mp3", "results")
```

```python
from diarizator import diarize

result_dir = diarize("conversation.mp3", "results", speaker_count_mode="exact", num_speakers=2)
```

## CLI

```text
diarizator inspect AUDIO
diarizator run AUDIO --output results
diarizator run AUDIO --speaker-count exact --num-speakers 2 --output results
diarizator run AUDIO --speaker-count bounded --min-speakers 2 --max-speakers 5 --output results
diarizator validate RUN_DIRECTORY
diarizator bundle RUN_DIRECTORY --output RESULT.zip
diarizator environment
diarizator demo --inspect
```

Local authenticated runs read `HF_TOKEN` from the environment. Exact mode records the count as oracle information; estimated is the default; bounded requires distinct valid minimum and maximum values.

## Controlled demonstration

The optional recording is a **Controlled two-character dialogue performed in one continuous take by one consenting speaker.** It is for functional demonstration, not evidence of general diarization accuracy. It has no reviewed reference RTTM, so this project reports no DER or JER for it. See [the demo documentation](examples/controlled_demo/README.md) and its separate CC BY 4.0 license declaration.

## Outputs, privacy, and limitations

Runs produce TXT, SRT, JSON, JSONL, RTTM, environment, provenance, timing, memory, validation, and log artifacts. Bundles exclude source/canonical audio, credentials, caches, weights, checkpoints, and absolute private paths by default. Processing happens in the user's local or Colab runtime; model weights come from their official providers, and no proprietary diarization API receives the audio.

Users must have the rights and consent required to process recordings and remain responsible for applicable laws. Speaker labels are anonymous and may be wrong. Overlap, noise, accents, short turns, domain shift, and ASR errors can reduce quality. No formal accuracy claim is made without a reviewed reference RTTM.

More detail: [authentication](docs/authentication.md), [Colab](docs/colab.md), [outputs](docs/outputs.md), [architecture](docs/architecture.md), [privacy](docs/privacy_and_consent.md), and [troubleshooting](docs/troubleshooting.md).

## Installation and development

Before the first tag:

```bash
pip install "diarizator @ git+https://github.com/Favioleiva/diarizator.git@main"
```

For development: `pip install -e ".[dev]"`, then `pytest`. Public CI is CPU-only and never runs gated models.

## License, notices, and citation

Original software is MIT licensed. The demo audio has its own CC BY 4.0 declaration. Model weights and third-party components keep their own licenses and conditions; see [third-party notices](THIRD_PARTY_NOTICES.md). Cite this package using [CITATION.cff](CITATION.cff). Copyright © 2026 Favio Leiva.
