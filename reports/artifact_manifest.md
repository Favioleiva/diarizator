# Artifact manifest

The public candidate contains these intentional artifact classes:

| Class | Location | Publication policy |
|---|---|---|
| Python package | `src/diarizator/` | Include |
| Public notebook | `notebooks/Diarizator_Community1_Colab.ipynb` | Include, output-free |
| Colab profile | `colab/` | Include |
| Configuration | `configs/` | Include |
| Documentation | `README.md`, `docs/`, policy and citation files | Include |
| Controlled demo | `examples/controlled_demo/` | Include exactly one MP3 plus rights/metadata/draft transcript docs |
| Tests and validators | `tests/`, `scripts/` | Include |
| CI | `.github/workflows/` | Include, CPU-only |
| Audit reports | `reports/` | Include |
| Build products | `dist/`, `build/`, `*.egg-info` | Exclude from Git |
| Validation environments/caches | `.validation-*`, caches | Exclude from Git |

The repository scanner is the authoritative file-level allowlist check and reports the final public file count before commit. The approved MP3 hash is recorded in `demo_manifest.json`; distribution archives are reproducible build outputs and are not committed.
