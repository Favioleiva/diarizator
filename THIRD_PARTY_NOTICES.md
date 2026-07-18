# Third-party notices

Diarizator's original source code is released under the MIT License. It does
not redistribute model weights. Users download models from their official
providers under those providers' terms.

| Component | Role | License/access | Official source |
|---|---|---|---|
| pyannote.audio | Diarization framework | MIT | https://github.com/pyannote/pyannote-audio |
| `pyannote/speaker-diarization-community-1` | Default diarization model | CC BY 4.0 weights; gated Hugging Face access and accepted model conditions required | https://huggingface.co/pyannote/speaker-diarization-community-1 |
| faster-whisper | Whisper inference | MIT | https://github.com/SYSTRAN/faster-whisper |
| OpenAI Whisper | ASR model architecture/weights | MIT; model terms remain those of the official provider | https://github.com/openai/whisper |
| CTranslate2 | Neural inference runtime | MIT | https://github.com/OpenNMT/CTranslate2 |
| PyTorch | Tensor and GPU runtime | BSD-style license | https://github.com/pytorch/pytorch |
| Hugging Face Hub | Model distribution/authentication client | Apache-2.0 | https://github.com/huggingface/huggingface_hub |
| FFmpeg | Media probing/decoding | Primarily LGPL 2.1-or-later; a particular build may enable GPL components | https://ffmpeg.org/legal.html |

Community-1 and Whisper weights are not part of this repository, wheel, or
source distribution. Diarizator does not claim ownership of any upstream code,
model, paper, trademark, or dataset.

The bundled demonstration recording has a separate license documented in
`examples/controlled_demo/AUDIO_LICENSE.md`; it is not covered by the software
MIT License.
