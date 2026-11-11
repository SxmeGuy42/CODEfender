"""
Testovací soubor: SQL Injection v Pythonu
Tento kód ÚMYSLNĚ obsahuje bezpečnostní chyby pro testování agenta.
"""

import sqlite3

def get_user_by_id(user_id):
    """
    ZRANITELNÁ FUNKCE - SQL Injection
    """
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    # NEBEZPEČNÉ: Přímá konkatenace vstupu do SQL dotazu
    query = f"SELECT * FROM users WHERE id = {user_id}"
    cursor.execute(query)
    
    result = cursor.fetchone()
    conn.close()
    return result


def search_users(username):
    """
    ZRANITELNÁ FUNKCE - SQL Injection přes string formatting
    """
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    # NEBEZPEČNÉ: Použití % formátování
    query = "SELECT * FROM users WHERE username = '%s'" % username
    cursor.execute(query)
    
    results = cursor.fetchall()
    conn.close()
    return results


def login(username, password):
    """
    DALŠÍ ZRANITELNOST - Kombinace SQL injection a slabého hashování
    """
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    # NEBEZPEČNÉ: SQL injection + MD5 pro hesla
    import hashlib
    password_hash = hashlib.md5(password.encode()).hexdigest()
    
    query = f"SELECT * FROM users WHERE username = '{username}' AND password = '{password_hash}'"
    cursor.execute(query)
    
    user = cursor.fetchone()
    conn.close()
    
    if user:
        return {"status": "success", "user": user}
    return {"status": "failed"}
