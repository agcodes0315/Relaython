
import os
import shutil
import stat
import subprocess
import zipfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
REAL_SCRIPT = REPO_ROOT / "scripts" / "build_lambda.sh"
REAL_HANDLER = REPO_ROOT / "lambda" / "resume_worker" / "handler.py"


def _bash() -> str:
    """Git Bash on Windows, the normal bash everywhere else."""
    if os.name == "nt":
        git_bash = r"C:\Program Files\Git\bin\bash.exe"
        if os.path.exists(git_bash):
            return git_bash
    return shutil.which("bash") or "bash"

pytestmark = pytest.mark.skipif(
    shutil.which("bash") is None,
    reason="bash is not available",
)


def make_workspace(tmp_path: Path, handler_text: str | None = None) -> Path:
    """A throwaway repo layout: scripts/build_lambda.sh + the handler."""
    (tmp_path / "scripts").mkdir()
    (tmp_path / "lambda" / "resume_worker").mkdir(parents=True)

    shutil.copy(REAL_SCRIPT, tmp_path / "scripts" / "build_lambda.sh")

    target = tmp_path / "lambda" / "resume_worker" / "handler.py"

    if handler_text is None:
        shutil.copy(REAL_HANDLER, target)
    else:
        target.write_text(handler_text, encoding="utf-8")

    return tmp_path


def make_fake_aws(tmp_path: Path) -> Path:
    """A fake 'aws' that records its arguments and answers one question."""
    bin_dir = tmp_path / "fakebin"
    bin_dir.mkdir()

    fake = bin_dir / "aws"
    fake.write_text(
        "#!/usr/bin/env bash\n"
        'echo "$@" >> "$AWS_CALLS_FILE"\n'
        'if [ "$1 $2" = "lambda get-function-configuration" ]; then\n'
        '  echo "$FAKE_HANDLER"\n'
        "fi\n",
        encoding="utf-8",
    )
    fake.chmod(fake.stat().st_mode | stat.S_IEXEC)

    return bin_dir


def run_script(workspace: Path, bin_dir: Path, **extra_env):
    env = dict(os.environ)
    env["PATH"] = f"{bin_dir}{os.pathsep}{env['PATH']}"
    env["AWS_CALLS_FILE"] = str(workspace / "aws_calls.txt")
    env["FAKE_HANDLER"] = "handler.lambda_handler"
    env.pop("DEPLOY", None)
    env.update(extra_env)

    return subprocess.run(
        [_bash(), "scripts/build_lambda.sh"],
        cwd=workspace,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )


def aws_calls(workspace: Path) -> list[str]:
    path = workspace / "aws_calls.txt"

    if not path.exists():
        return []

    return path.read_text(encoding="utf-8").strip().splitlines()


# --------------------------------------------------------------- the script


def test_script_file_is_a_clean_bash_script():
    raw = REAL_SCRIPT.read_bytes()

    assert raw.startswith(b"#!/usr/bin/env bash\n")
    assert b"\r\n" not in raw          # Windows line endings break bash
    assert b"set -euo pipefail" in raw


def test_build_creates_a_zip_with_handler_py_at_the_top_level(tmp_path):
    workspace = make_workspace(tmp_path)
    result = run_script(workspace, make_fake_aws(tmp_path))

    zip_path = workspace / "build" / "relay_resume_worker.zip"

    assert result.returncode == 0, result.stderr
    assert zip_path.exists()

    with zipfile.ZipFile(zip_path) as archive:
        assert archive.namelist() == ["handler.py"]
        assert archive.read("handler.py") == REAL_HANDLER.read_bytes()


def test_build_without_deploy_never_calls_aws(tmp_path):
    workspace = make_workspace(tmp_path)
    result = run_script(workspace, make_fake_aws(tmp_path))

    assert result.returncode == 0, result.stderr
    assert aws_calls(workspace) == []
    assert "DEPLOY=1" in result.stdout


def test_build_prints_the_handler_name_reminder(tmp_path):
    workspace = make_workspace(tmp_path)
    result = run_script(workspace, make_fake_aws(tmp_path))

    assert "handler.lambda_handler" in result.stdout


def test_building_twice_replaces_the_old_zip(tmp_path):
    workspace = make_workspace(tmp_path)
    bin_dir = make_fake_aws(tmp_path)

    run_script(workspace, bin_dir)
    second = run_script(workspace, bin_dir)

    with zipfile.ZipFile(workspace / "build" / "relay_resume_worker.zip") as archive:
        assert archive.namelist() == ["handler.py"]

    assert second.returncode == 0


def test_script_refuses_a_handler_that_imports_relay(tmp_path):
    workspace = make_workspace(
        tmp_path,
        handler_text="import os\nfrom relay.store import get_task\n",
    )
    result = run_script(workspace, make_fake_aws(tmp_path))

    assert result.returncode != 0
    assert "standalone" in result.stderr
    assert not (workspace / "build" / "relay_resume_worker.zip").exists()


def test_script_fails_clearly_when_the_handler_is_missing(tmp_path):
    workspace = make_workspace(tmp_path)
    (workspace / "lambda" / "resume_worker" / "handler.py").unlink()

    result = run_script(workspace, make_fake_aws(tmp_path))

    assert result.returncode != 0
    assert "handler.py" in result.stderr


# ------------------------------------------------------------------ deploy


def test_deploy_uploads_the_zip_to_the_right_function_and_region(tmp_path):
    workspace = make_workspace(tmp_path)
    result = run_script(workspace, make_fake_aws(tmp_path), DEPLOY="1")
    calls = aws_calls(workspace)

    assert result.returncode == 0, result.stderr

    upload = next(c for c in calls if c.startswith("lambda update-function-code"))

    assert "--function-name RelayResumeWorker" in upload
    assert "--region us-west-2" in upload
    assert "--zip-file fileb://" in upload
    assert upload.rstrip().split("--zip-file fileb://")[1].split()[0].endswith(
        "build/relay_resume_worker.zip"
    )


def test_deploy_waits_for_the_update_before_checking_the_handler_setting(tmp_path):
    workspace = make_workspace(tmp_path)
    run_script(workspace, make_fake_aws(tmp_path), DEPLOY="1")
    calls = aws_calls(workspace)

    order = [c.split()[1] for c in calls if c.startswith("lambda")]

    assert order == ["update-function-code", "wait", "get-function-configuration"]


def test_deploy_is_quiet_when_the_handler_setting_is_already_correct(tmp_path):
    workspace = make_workspace(tmp_path)
    result = run_script(
        workspace,
        make_fake_aws(tmp_path),
        DEPLOY="1",
        FAKE_HANDLER="handler.lambda_handler",
    )

    assert "WARNING" not in result.stdout


def test_deploy_warns_when_the_handler_setting_is_still_the_old_one(tmp_path):
    workspace = make_workspace(tmp_path)
    result = run_script(
        workspace,
        make_fake_aws(tmp_path),
        DEPLOY="1",
        FAKE_HANDLER="relay_resume_lambda.lambda_handler",
    )

    assert result.returncode == 0
    assert "WARNING" in result.stdout
    assert "relay_resume_lambda.lambda_handler" in result.stdout
    assert "update-function-configuration" in result.stdout
    assert "--handler handler.lambda_handler" in result.stdout

    # It only TELLS you the fix; it never changes AWS settings on its own.
    assert not any(c.startswith("lambda update-function-configuration") for c in aws_calls(workspace))


def test_function_name_and_region_can_be_overridden(tmp_path):
    workspace = make_workspace(tmp_path)
    run_script(
        workspace,
        make_fake_aws(tmp_path),
        DEPLOY="1",
        RELAY_RESUME_LAMBDA="MyOtherWorker",
        RELAY_DEPLOY_REGION="eu-west-1",
    )
    upload = next(c for c in aws_calls(workspace) if c.startswith("lambda update-function-code"))

    assert "--function-name MyOtherWorker" in upload
    assert "--region eu-west-1" in upload


def test_a_stray_aws_region_variable_does_not_redirect_the_deploy(tmp_path):
    # Many Macs have AWS_REGION set for other projects. The deploy must still
    # go to us-west-2 unless RELAY_DEPLOY_REGION says otherwise.
    workspace = make_workspace(tmp_path)
    run_script(workspace, make_fake_aws(tmp_path), DEPLOY="1", AWS_REGION="ap-south-1")
    upload = next(c for c in aws_calls(workspace) if c.startswith("lambda update-function-code"))

    assert "--region us-west-2" in upload