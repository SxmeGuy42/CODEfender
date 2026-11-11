"""
Testovací soubor: Command Injection v Pythonu
"""

import os
import subprocess

def ping_host(hostname):
    """
    ZRANITELNÁ FUNKCE - Command Injection
    """
    # NEBEZPEČNÉ: Uživatelský vstup přímo v system()
    os.system(f"ping -c 4 {hostname}")


def backup_file(filename):
    """
    ZRANITELNÁ FUNKCE - Command Injection přes subprocess
    """
    # NEBEZPEČNÉ: shell=True s uživatelským vstupem
    subprocess.call(f"tar -czf backup.tar.gz {filename}", shell=True)


def execute_script(script_name):
    """
    VELMI NEBEZPEČNÉ - eval() s uživatelským vstupem
    """
    # KRITICKÁ CHYBA: eval() umožňuje spuštění libovolného kódu
    result = eval(script_name)
    return result


# Hardcoded credentials - další bezpečnostní problém
API_KEY = "sk_live_1234567890abcdef"
DATABASE_PASSWORD = "admin123"
SECRET_TOKEN = "my_secret_token_12345"
