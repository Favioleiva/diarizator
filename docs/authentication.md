# Authentication

Community-1 is gated. Sign in to Hugging Face, visit the [official model card](https://huggingface.co/pyannote/speaker-diarization-community-1), accept its access conditions, and create a read token. In Colab, store it as `HF_TOKEN` under the key icon and grant notebook access. Locally, set the `HF_TOKEN` environment variable or use an already cached model snapshot.

Diarizator preflights access before ASR and distinguishes missing credentials, rejected credentials, unaccepted terms, network failure, cached access, and incompatible dependencies. It never prints, logs, serializes, bundles, or passes the token on a command line.
