import subprocess
import sys

MAIN = ["python", "main.py"]

# Use a real hash if you want approve to succeed.
# For parser testing it just needs to be 64 hex chars.
VALID_HASH = "5083db379b25a1c70586bd2e5cf1d2f19f9717880ac53b0c9ea238c840f27e4b"


tests = [
    {
        "name": "valid approve command",
        "cmd": f"plan.approve:{VALID_HASH}",
        "expect_denied": False,
    },
    {
        "name": "invalid hash length",
        "cmd": "plan.approve:abc",
        "expect_denied": True,
    },
    {
        "name": "whitespace in hash",
        "cmd": "plan.approve:abc def",
        "expect_denied": True,
    },
    {
        "name": "unknown command",
        "cmd": "plan.delete:abc",
        "expect_denied": True,
    },
    {
        "name": "missing colon",
        "cmd": "plan.approve",
        "expect_denied": True,
    },
    {
        "name": "valid submit passes parser",
        "cmd": 'plan.submit:{"plan_id":"parser-test","steps":[]}',
        "expect_denied": False,
    },
    {
        "name": "extra colon in approve",
        "cmd": f"plan.approve:{VALID_HASH}:extra",
        "expect_denied": True,
    },
]


def run_test(test):
    print(f"\n--- {test['name']} ---")

    proc = subprocess.run(
        MAIN + [test["cmd"]],
        capture_output=True,
        text=True,
    )

    output = (proc.stdout + proc.stderr).strip()

    denied = "DENIED" in output

    if denied == test["expect_denied"]:
        print("PASS")
    else:
        print("FAIL")

    print("command:", test["cmd"])
    print("output:")
    print(output)


def main():
    print("Parser smoke tests")
    print("==================")

    for test in tests:
        run_test(test)


if __name__ == "__main__":
    main()
