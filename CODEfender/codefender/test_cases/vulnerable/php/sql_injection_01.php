<?php
/**
 * Testovací soubor: SQL Injection v PHP
 * Tento kód ÚMYSLNĚ obsahuje bezpečnostní chyby.
 */

// NEBEZPEČNÉ: Přímá konkatenace vstupu do SQL
function getUserById($id) {
    $conn = mysqli_connect("localhost", "user", "password", "database");
    
    // SQL INJECTION ZRANITELNOST
    $query = "SELECT * FROM users WHERE id = $id";
    $result = mysqli_query($conn, $query);
    
    return mysqli_fetch_assoc($result);
}

// NEBEZPEČNÉ: Žádná sanitizace vstupu
function searchUsers($username) {
    $conn = mysqli_connect("localhost", "user", "password", "database");
    
    // SQL INJECTION přes GET parametr
    $query = "SELECT * FROM users WHERE username = '" . $_GET['username'] . "'";
    $result = mysqli_query($conn, $query);
    
    return mysqli_fetch_all($result, MYSQLI_ASSOC);
}

// NEBEZPEČNÉ: Slabé hashování + SQL injection
function login($username, $password) {
    $conn = mysqli_connect("localhost", "user", "password", "database");
    
    // MD5 je slabý pro hesla
    $password_hash = md5($password);
    
    // SQL INJECTION v obou parametrech
    $query = "SELECT * FROM users WHERE username = '$username' AND password = '$password_hash'";
    $result = mysqli_query($conn, $query);
    
    if (mysqli_num_rows($result) > 0) {
        $_SESSION['user'] = mysqli_fetch_assoc($result);
        return true;
    }
    return false;
}

// HARDCODED CREDENTIALS
$db_password = "admin123";
$api_key = "1234567890abcdef";

?>
