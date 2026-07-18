# Google Colab

Open [`Diarizator_Community1_Colab.ipynb`](../notebooks/Diarizator_Community1_Colab.ipynb), choose a GPU runtime, add the `HF_TOKEN` secret, and select **Run all**. The notebook installs from this repository, checks NumPy/SciPy in a fresh process, uses a safe manual two-pass restart when necessary, asks for one upload, validates it with FFprobe, runs the package, creates a sanitized ZIP, and starts the browser download.

Google Drive and local path editing are not part of the workflow. The default is estimated speaker count. An optional configuration cell exposes exact and bounded modes; demo mode may use its known exact count of two.
