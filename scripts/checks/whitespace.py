import subprocess

result = subprocess.run(["git", "diff", "--check"], check=False)
cached = subprocess.run(["git", "diff", "--cached", "--check"], check=False)
raise SystemExit(result.returncode or cached.returncode)
