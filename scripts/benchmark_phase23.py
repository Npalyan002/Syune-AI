from benchmarks.phase23 import run

if __name__ == "__main__":
    import json
    print(json.dumps(run(),indent=2,sort_keys=True))
