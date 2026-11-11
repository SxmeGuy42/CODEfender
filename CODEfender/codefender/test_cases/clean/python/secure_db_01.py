"""
Testovací soubor: Bezpečné databázové operace v Pythonu
Tento kód by NEMĚL vyvolat bezpečnostní varování.
"""

import sqlite3
import os
from typing import Optional, Dict, Any
import bcrypt


def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    """
    BEZPEČNÁ FUNKCE - Parametrizovaný SQL dotaz
    """
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    # SPRÁVNĚ: Použití parametrizovaného dotazu
    query = "SELECT * FROM users WHERE id = ?"
    cursor.execute(query, (user_id,))
    
    result = cursor.fetchone()
    conn.close()
    return result


def search_users(username: str) -> list:
    """
    BEZPEČNÁ FUNKCE - Parametrizované dotazy s validací
    """
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    # SPRÁVNĚ: Parametrizovaný dotaz
    query = "SELECT id, username, email FROM users WHERE username = ?"
    cursor.execute(query, (username,))
    
    results = cursor.fetchall()
    conn.close()
    return results


def login(username: str, password: str) -> Dict[str, Any]:
    """
    BEZPEČNÁ FUNKCE - Bcrypt hashování + parametrizované dotazy
    """
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    # SPRÁVNĚ: Parametrizovaný dotaz
    query = "SELECT id, username, password_hash FROM users WHERE username = ?"
    cursor.execute(query, (username,))
    
    user = cursor.fetchone()
    conn.close()
    
    if user and bcrypt.checkpw(password.encode(), user[2].encode()):
        return {"status": "success", "user_id": user[0], "username": user[1]}
    
    return {"status": "failed"}


def create_user(username: str, email: str, password: str) -> bool:
    """
    BEZPEČNÁ FUNKCE - Bcrypt pro hashování hesel
    """
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    # SPRÁVNĚ: Použití bcrypt pro hashování
    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
    
    # SPRÁVNĚ: Parametrizovaný INSERT
    query = "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)"
    
    try:
        cursor.execute(query, (username, email, password_hash.decode()))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def get_api_key() -> str:
    """
    BEZPEČNÁ FUNKCE - Získání API klíče z proměnných prostředí
    """
    # SPRÁVNĚ: Použití environment variables místo hardcoded secrets
    api_key = os.getenv('API_KEY')
    
    if not api_key:
        raise ValueError("API_KEY není nastaven v environment variables")
    
    return api_key
