/**
 * Testovací soubor: XSS v JavaScriptu
 * Tento kód ÚMYSLNĚ obsahuje bezpečnostní chyby.
 */

// NEBEZPEČNÉ: Přímé vložení uživatelského vstupu do innerHTML
function displayUserMessage(message) {
    const container = document.getElementById('message-container');
    // XSS ZRANITELNOST
    container.innerHTML = message;
}

// NEBEZPEČNÉ: eval() s uživatelským vstupem
function executeUserCode(code) {
    // KRITICKÁ CHYBA - umožňuje spuštění libovolného JS kódu
    eval(code);
}

// NEBEZPEČNÉ: document.write s uživatelským vstupem
function showGreeting(name) {
    // XSS přes document.write
    document.write("<h1>Ahoj, " + name + "!</h1>");
}

// NEBEZPEČNÉ: Bez validace URL pro redirect
function redirectUser() {
    const url = new URLSearchParams(window.location.search).get('redirect');
    // OPEN REDIRECT zranitelnost
    window.location.href = url;
}

// HARDCODED API KEYS
const API_KEY = 'sk_live_1234567890abcdef';
const SECRET_TOKEN = 'secret_token_xyz';
const DATABASE_URL = 'mongodb://admin:password123@localhost:27017/mydb';

// NEBEZPEČNÉ: localStorage pro citlivá data
function saveUserData(userData) {
    // Ukládání citlivých dat v localStorage (nezašifrováno)
    localStorage.setItem('user', JSON.stringify(userData));
    localStorage.setItem('token', userData.authToken);
}

// NEBEZPEČNÉ: CORS nastavení
const corsConfig = {
    origin: '*', // Povoluje všechny domény
    credentials: true
};

module.exports = {
    displayUserMessage,
    executeUserCode,
    showGreeting,
    redirectUser
};
