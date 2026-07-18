# Dependency strategy

The core wheel has no mandatory model dependency, so metadata inspection and the public types remain lightweight. The `inference` extra uses compatibility ranges. Colab uses separately maintained direct requirements and exact constraints derived from the accepted run: NumPy 2.2.2, SciPy 1.16.3, pandas 2.2.3, Jedi 0.19.2, and OpenTelemetry 1.42.1 restrictions. Torch/CUDA remain Colab-provided and are inspected, not replaced. Future Colab images require revalidation.
