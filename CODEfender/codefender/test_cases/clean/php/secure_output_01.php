<?php
/**
 * Testovací soubor: Bezpečný výstup v PHP (ochrana proti XSS)
 */

// SPRÁVNĚ: Escapování výstupu pomocí htmlspecialchars()
function displayUserGreeting($name) {
    // BEZPEČNÉ: Escapování HTML entit
    $safe_name = htmlspecialchars($name, ENT_QUOTES, 'UTF-8');
    echo "<h1>Vítej, $safe_name!</h1>";
}

// SPRÁVNĚ: Sanitizace komentáře před výpisem
function showComment($comment_id) {
    $pdo = getDatabaseConnection();
    
    $stmt = $pdo->prepare("SELECT comment FROM comments WHERE id = :id");
    $stmt->bindParam(':id', $comment_id, PDO::PARAM_INT);
    $stmt->execute();
    
    $comment = $stmt->fetch(PDO::FETCH_ASSOC)['comment'];
    
    // BEZPEČNÉ: Escapování před výpisem
    $safe_comment = htmlspecialchars($comment, ENT_QUOTES, 'UTF-8');
    echo "<div class='comment'>$safe_comment</div>";
}

// SPRÁVNĚ: Whitelist validace pro page parameter
function loadPage() {
    $page = $_GET['page'] ?? 'home';
    
    // BEZPEČNÉ: Whitelist povolených stránek
    $allowed_pages = ['home', 'about', 'contact', 'products'];
    
    if (!in_array($page, $allowed_pages)) {
        $page = 'home'; // Výchozí stránka
    }
    
    include($page . ".php");
}

// SPRÁVNĚ: Validace a sanitizace vstupu
function processUserInput($input) {
    // Odstranění HTML tagů
    $clean_input = strip_tags($input);
    
    // Escapování pro bezpečné zobrazení
    $safe_input = htmlspecialchars($clean_input, ENT_QUOTES, 'UTF-8');
    
    return $safe_input;
}

// SPRÁVNĚ: Content Security Policy header
function setSecurityHeaders() {
    header("Content-Security-Policy: default-src 'self'; script-src 'self'");
    header("X-Content-Type-Options: nosniff");
    header("X-Frame-Options: DENY");
    header("X-XSS-Protection: 1; mode=block");
}

// SPRÁVNĚ: Session security
function initSecureSession() {
    // Bezpečné session cookies
    ini_set('session.cookie_httponly', 1);
    ini_set('session.cookie_secure', 1);
    ini_set('session.cookie_samesite', 'Strict');
    
    session_start();
    
    // Ochrana proti session fixation
    if (!isset($_SESSION['initiated'])) {
        session_regenerate_id(true);
        $_SESSION['initiated'] = true;
    }
}

// SPRÁVNĚ: CSRF token
function generateCSRFToken() {
    if (empty($_SESSION['csrf_token'])) {
        $_SESSION['csrf_token'] = bin2hex(random_bytes(32));
    }
    return $_SESSION['csrf_token'];
}

function validateCSRFToken($token) {
    if (!isset($_SESSION['csrf_token'])) {
        return false;
    }
    
    return hash_equals($_SESSION['csrf_token'], $token);
}

?>
