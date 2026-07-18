# Troubleshooting

- `TOKEN_MISSING`: add `HF_TOKEN` to Colab Secrets or the local environment.
- `ACCESS_NOT_ACCEPTED`: accept the Community-1 conditions on its official model page.
- `TOKEN_REJECTED`: replace the token with a valid read token; do not paste it into logs or issues.
- `NETWORK_UNAVAILABLE`: verify Hugging Face and package-index access.
- `INCOMPATIBLE_STACK`: restart the Colab session after the dependency cell and choose **Run all** again.
- FFprobe/FFmpeg error: verify that the file is a supported, decodable media file, not merely renamed.
- GPU out of memory: the validated policy reduces ASR batch size and may use the smaller CPU fallback when permitted.

When reporting a problem, attach sanitized environment and validation JSON only—never audio, tokens, caches, or private paths unless you intentionally choose to share them.
