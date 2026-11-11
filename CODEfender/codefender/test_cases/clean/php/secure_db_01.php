<?php
/**
 * Testovací soubor: Bezpečné databázové operace v PHP
 * Tento kód by NEMĚL vyvolat bezpečnostní varování.
 */

// SPRÁVNĚ: Použití PDO s prepared statements
function getUserById($id) {
    $dsn = "mysql:host=localhost;dbname=database";
    $pdo = new PDO($dsn, getenv('DB_USER'), getenv('DB_PASSWORD'));
    
    // BEZPEČNÉ: Prepared statement s bind parametrem
    $stmt = $pdo->prepare("SELECT * FROM users WHERE id = :id");
    $stmt->bindParam(':id', $id, PDO::PARAM_INT);
    $stmt->execute();
    
    return $stmt->fetch(PDO::FETCH_ASSOC);
}

// SPRÁVNĚ: Prepared statements pro vyhledávání
function searchUsers($username) {
    $dsn = "mysql:host=localhost;dbname=database";
    $pdo = new PDO($dsn, getenv('DB_USER'), getenv('DB_PASSWORD'));
    
    // BEZPEČNÉ: Prepared statement
    $stmt = $pdo->prepare("SELECT id, username, email FROM users WHERE username = :username");
    $stmt->bindParam(':username', $username, PDO::PARAM_STR);
    $stmt->execute();
    
    return $stmt->fetchAll(PDO::FETCH_ASSOC);
}

// SPRÁVNĚ: Bcrypt pro hesla + prepared statements
function login($username, $password) {
    $dsn = "mysql:host=localhost;dbname=database";
    $pdo = new PDO($dsn, getenv('DB_USER'), getenv('DB_PASSWORD'));
    
    // BEZPEČNÉ: Prepared statement
    $stmt = $pdo->prepare("SELECT id, username, password_hash FROM users WHERE username = :username");
    $stmt->bindParam(':username', $username, PDO::PARAM_STR);
    $stmt->execute();
    
    $user = $stmt->fetch(PDO::FETCH_ASSOC);
    
    if ($user && password_verify($password, $user['password_hash'])) {
        // SPRÁVNĚ: Regenerace session ID po přihlášení
        session_regenerate_id(true);
        $_SESSION['user_id'] = $user['id'];
        $_SESSION['username'] = $user['username'];
        return true;
    }
    
    return false;
}

// SPRÁVNĚ: Password hashing s password_hash()
function createUser($username, $email, $password) {
    $dsn = "mysql:host=localhost;dbname=database";
    $pdo = new PDO($dsn, getenv('DB_USER'), getenv('DB_PASSWORD'));
    
    // SPRÁVNĚ: Použití password_hash() místo MD5
    $password_hash = password_hash($password, PASSWORD_BCRYPT);
    
    // BEZPEČNÉ: Prepared statement pro INSERT
    $stmt = $pdo->prepare("INSERT INTO users (username, email, password_hash) VALUES (:username, :email, :password_hash)");
    $stmt->bindParam(':username', $username, PDO::PARAM_STR);
    $stmt->bindParam(':email', $email, PDO::PARAM_STR);
    $stmt->bindParam(':password_hash', $password_hash, PDO::PARAM_STR);
    
    try {
        $stmt->execute();
        return true;
    } catch (PDOException $e) {
        error_log("Database error: " . $e->getMessage());
        return false;
    }
}

// SPRÁVNĚ: Environment variables místo hardcoded credentials
function getDatabaseConnection() {
    $dsn = "mysql:host=localhost;dbname=database";
    $username = getenv('DB_USER');
    $password = getenv('DB_PASSWORD');
    
    if (!$username || !$password) {
        throw new Exception("Database credentials not configured");
    }
    
    return new PDO($dsn, $username, $password, [
        PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
        PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC
    ]);
}

?>
