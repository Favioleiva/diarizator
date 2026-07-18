# Security policy

Please report security or privacy issues privately through GitHub's security
advisory feature for `Favioleiva/diarizator`. Do not open a public issue that
contains tokens, credentials, private audio, private transcripts, or signed
download URLs.

Diarizator never needs a token in a command-line argument. Use Colab Secrets or
the local `HF_TOKEN` environment variable. Revoke a token immediately if it is
ever exposed. Result bundles exclude source audio, environment-variable values,
model caches, and credentials by default.

Version 0.1.0 is a candidate and has no long-term security-support guarantee.
