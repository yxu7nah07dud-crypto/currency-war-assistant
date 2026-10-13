"""Validate the frozen executable, including WGC capture of its own test window."""
from pathlib import Path
import json
import subprocess
import sys


def main():
    root=Path(__file__).resolve().parent.parent
    arguments=[value for value in sys.argv[1:] if value!='--check-game']
    program=Path(arguments[0]) if arguments else root/'dist/CurrencyWarAssistant/CurrencyWarAssistant.exe'
    output=root/'outputs/release-self-test.json'
    output.parent.mkdir(exist_ok=True)
    if output.exists():output.unlink()
    extra=['--check-game'] if '--check-game' in sys.argv else []
    completed=subprocess.run([str(program),'--self-test',str(output),*extra],timeout=30)
    if not output.exists():raise RuntimeError(f'Release did not write a self-test report (exit {completed.returncode})')
    report=json.loads(output.read_text(encoding='utf8'))
    print(json.dumps(report,ensure_ascii=False,indent=2))
    if completed.returncode or not report.get('ok') or not report.get('frozen'):
        raise RuntimeError('Frozen release self-test failed')


if __name__=='__main__':
    main()
