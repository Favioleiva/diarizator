import json
from diarizator.environment import capture_environment

print(json.dumps(capture_environment(), indent=2, sort_keys=True))
