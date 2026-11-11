<?php
/**
 * Testovací soubor: XSS (Cross-Site Scripting) v PHP
 */

// NEBEZPEČNÉ: Neescapovaný výstup z GET parametru
function displayUserGreeting() {
    $name = $_GET['name'];
    // XSS ZRANITELNOST - žádné escapování
    echo "<h1>Vítej, $name!</h1>";
}

// NEBEZPEČNÉ: Výpis komentáře bez sanitizace
function showComment($comment_id) {
    $conn = mysqli_connect("localhost", "user", "password", "database");
    $query = "SELECT comment FROM comments WHERE id = $comment_id";
    $result = mysqli_query($conn, $query);
    $comment = mysqli_fetch_assoc($result)['comment'];
    
    // XSS - přímý výpis bez htmlspecialchars()
    echo "<div class='comment'>$comment</div>";
}

// NEBEZPEČNÉ: eval() s uživatelským vstupem
function executeCode() {
    $code = $_POST['code'];
    // REMOTE CODE EXECUTION riziko
    eval($code);
}

// NEBEZPEČNÉ: File inclusion
function loadPage() {
    $page = $_GET['page'];
    // LOCAL FILE INCLUSION zranitelnost
    include($page . ".php");
}

// Session fixation - chybějící regenerace ID
function userLogin($username, $password) {
    // Chybí session_regenerate_id(true)
    $_SESSION['logged_in'] = true;
    $_SESSION['username'] = $username;
}

?>
