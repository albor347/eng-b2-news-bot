import os
import subprocess
import datetime


def test_dry_run_creates_markdown(tmp_path):
    md_path = tmp_path / f"{datetime.date.today().isoformat()}_bne_b2.md"
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    script = os.path.join(repo_root, 'bne_b2_bot.py')
    subprocess.run([
        'python', script, '--dry-run'], check=False, cwd=tmp_path)
    assert md_path.exists()
