"""System utilities — CVE pattern: shell injection via subprocess with shell=True."""
import subprocess
import os


def ping_host(hostname: str) -> str:
    # Vulnerable: shell=True + user-controlled hostname → command injection
    result = subprocess.run(
        f"ping -c 1 {hostname}",
        shell=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def convert_image(input_path: str, output_path: str) -> int:
    # Vulnerable: both paths come from user input
    cmd = f"convert {input_path} {output_path}"
    return os.system(cmd)


def run_linter(filename: str) -> str:
    # Vulnerable: filename is user-supplied
    proc = subprocess.Popen(
        "pylint " + filename,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    out, _ = proc.communicate()
    return out.decode()
