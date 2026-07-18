# Validated Colab dependency profile

This profile preserves the dependency strategy and binary checks from the accepted Phase 1 notebook. NumPy and SciPy are installed together and then imported in a fresh process. `pip check` output is accepted only for the two exact, documented Colab-image conflicts; any other conflict stops the notebook.

The profile was derived from a Google Colab Python 3.12 / CUDA 12.6 session. Colab images change, so revalidate it before each release. The portable package metadata deliberately does not force this CUDA profile on local users.
