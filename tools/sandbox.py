import os
import shutil
import subprocess
import tempfile
import uuid

from core.config import CONFIG

CODE = CONFIG["code"]
DOCKER = CODE["docker"]
MAX_OUTPUT = CODE["max_output"]
TIMEOUT_EXIT = 124  # exit code of the Unix `timeout` command
DOCKER_ERROR = 125  # `docker run` itself failed: the code never ran
OOM_EXIT = 137      # killed by SIGKILL: the memory limit was reached

_docker_ready = None
_warned = False


def tronque_code_cycle(texte, maximum=MAX_OUTPUT, garder="fin"):
    if len(texte) <= maximum:
       return texte
    return "truncated start" + texte[-maximum:]


def timeout_result(timeo):
    return {"stdout": "",
            "stderr": f"Timeout: the code did not finish within {timeo} seconds. Retry with a lower algorithmic complexity",
            "exit_code": TIMEOUT_EXIT,
            "timed_out": True}


def result(completed):
    return {"stdout": tronque_code_cycle(completed.stdout),
            "stderr": tronque_code_cycle(completed.stderr),
            "exit_code": completed.returncode,
            "timed_out": False}


def docker_ready():
    """Docker answers and the sandbox image is present (pulled once if needed)."""
    global _docker_ready
    if _docker_ready is None:
        _docker_ready = False
        if shutil.which("docker"):
            try:
                if subprocess.run(["docker", "info"], capture_output=True, timeout=15).returncode == 0:
                    image = DOCKER["image"]
                    if subprocess.run(["docker", "image", "inspect", image], capture_output=True).returncode:
                        print(f"[sandbox] pulling the Docker image {image}...")
                        subprocess.run(["docker", "pull", image], capture_output=True, timeout=600)
                    _docker_ready = subprocess.run(["docker", "image", "inspect", image],
                                                   capture_output=True).returncode == 0
            except (subprocess.TimeoutExpired, OSError):
                _docker_ready = False
    return _docker_ready


def docker_command(name, timeo):
    return ["docker", "run", "--rm", "-i", "--name", name,
            "--network", "none",
            "--read-only", "--tmpfs", f"/tmp:rw,size={DOCKER['tmp_size']}", "--workdir", "/tmp",
            "--memory", DOCKER["memory"], "--memory-swap", DOCKER["memory"],
            "--cpus", str(DOCKER["cpus"]), "--pids-limit", str(DOCKER["pids_limit"]),
            "--user", "65534:65534", "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
            DOCKER["image"],
            "timeout", "-k", "1", str(timeo), "python3", "-I", "-"]


def run_in_docker(code, timeo):
    name = f"sensia-sandbox-{uuid.uuid4().hex[:12]}"
    try:
        completed = subprocess.run(docker_command(name, timeo), input=code, capture_output=True,
                                   text=True, timeout=timeo + DOCKER["start_margin"])
    except subprocess.TimeoutExpired:
        subprocess.run(["docker", "kill", name], capture_output=True)
        return timeout_result(timeo)
    if completed.returncode == TIMEOUT_EXIT:
        return timeout_result(timeo)
    if completed.returncode == DOCKER_ERROR:
        return None
    if completed.returncode == OOM_EXIT and not completed.stderr:
        completed.stderr = (f"Killed: the code exceeded the memory limit of the sandbox "
                            f"({DOCKER['memory']}). Use less memory.")
    return result(completed)


def run_in_process(code, timeo):
    env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "LANG": "C.UTF-8"}
    with tempfile.TemporaryDirectory(prefix="sensia-sandbox-") as workdir:
        try:
            completed = subprocess.run(["python3", "-I", "-c", code], capture_output=True, text=True,
                                       timeout=timeo, cwd=workdir, env=env)
        except subprocess.TimeoutExpired:
            return timeout_result(timeo)
    return result(completed)


def run_python(code, timeo=CODE["execution_timeout"]):
    global _warned
    if CODE["sandbox"] == "docker":
        isolated = run_in_docker(code, timeo) if docker_ready() else None
        if isolated is not None:
            return isolated
        if not CODE["fallback_to_process"]:
            return {"stdout": "", "exit_code": 1, "timed_out": False,
                    "stderr": "The Docker sandbox is unavailable and fallback_to_process is disabled."}
        if not _warned:
            print("[sandbox] Docker unavailable: the code runs in a local process, NOT isolated.")
            _warned = True
    return run_in_process(code, timeo)
