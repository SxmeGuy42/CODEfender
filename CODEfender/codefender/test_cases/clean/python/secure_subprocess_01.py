"""
Testovací soubor: Bezpečné spouštění subprocess v Pythonu
"""

import subprocess
import shlex
import re
from typing import List


def ping_host(hostname: str) -> str:
    """
    BEZPEČNÁ FUNKCE - Validace vstupu + bezpečné subprocess volání
    """
    # SPRÁVNĚ: Validace hostname před použitím
    if not re.match(r'^[a-zA-Z0-9.-]+$', hostname):
        raise ValueError("Neplatný hostname")
    
    # SPRÁVNĚ: subprocess.run s argumenty jako list, shell=False
    result = subprocess.run(
        ['ping', '-c', '4', hostname],
        capture_output=True,
        text=True,
        timeout=10
    )
    
    return result.stdout


def backup_file(filename: str) -> bool:
    """
    BEZPEČNÁ FUNKCE - Whitelist validace + bezpečné subprocess
    """
    # SPRÁVNĚ: Validace cesty souboru
    allowed_extensions = ['.txt', '.log', '.json']
    if not any(filename.endswith(ext) for ext in allowed_extensions):
        raise ValueError("Nepodporovaný typ souboru")
    
    # SPRÁVNĚ: Použití shlex.quote pro escapování
    safe_filename = shlex.quote(filename)
    
    # SPRÁVNĚ: subprocess bez shell=True
    result = subprocess.run(
        ['tar', '-czf', 'backup.tar.gz', filename],
        capture_output=True,
        timeout=30
    )
    
    return result.returncode == 0


def list_directory(path: str) -> List[str]:
    """
    BEZPEČNÁ FUNKCE - Whitelist přístup k adresářům
    """
    # SPRÁVNĚ: Whitelist povolených adresářů
    allowed_paths = ['/var/log', '/tmp', '/home/user/data']
    
    if path not in allowed_paths:
        raise ValueError("Přístup k tomuto adresáři není povolen")
    
    # SPRÁVNĚ: Bezpečné subprocess volání
    result = subprocess.run(
        ['ls', '-la', path],
        capture_output=True,
        text=True,
        timeout=5
    )
    
    return result.stdout.split('\n')


def execute_safe_script(script_name: str) -> dict:
    """
    BEZPEČNÁ FUNKCE - Whitelist skriptů místo eval()
    """
    # SPRÁVNĚ: Whitelist povolených skriptů místo eval()
    allowed_scripts = {
        'backup': lambda: subprocess.run(['./backup.sh'], capture_output=True),
        'cleanup': lambda: subprocess.run(['./cleanup.sh'], capture_output=True),
        'status': lambda: subprocess.run(['./status.sh'], capture_output=True)
    }
    
    if script_name not in allowed_scripts:
        raise ValueError(f"Skript '{script_name}' není povolen")
    
    result = allowed_scripts[script_name]()
    
    return {
        'script': script_name,
        'returncode': result.returncode,
        'output': result.stdout
    }
