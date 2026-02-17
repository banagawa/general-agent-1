import sys
from agent_core.orchestrator import Orchestrator


def main():
    if len(sys.argv) < 2:
        print("Usage: python main.py '<task>'")
        return

    task = sys.argv[1]
    orchestrator = Orchestrator()
    result = orchestrator.handle(task)
    print(result)


if __name__ == "__main__":
    main()
