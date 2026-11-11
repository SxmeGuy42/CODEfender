/**
 * Testovací soubor: Bezpečné DOM manipulace v JavaScriptu
 * Tento kód by NEMĚL vyvolat bezpečnostní varování.
 */

// SPRÁVNĚ: Použití textContent místo innerHTML
function displayUserMessage(message) {
    const container = document.getElementById('message-container');
    
    // BEZPEČNÉ: textContent automaticky escapuje HTML
    container.textContent = message;
}

// SPRÁVNĚ: Použití DOMPurify pro sanitizaci HTML
function displayRichContent(htmlContent) {
    const container = document.getElementById('content-container');
    
    // BEZPEČNÉ: Sanitizace přes DOMPurify
    const cleanHTML = DOMPurify.sanitize(htmlContent);
    container.innerHTML = cleanHTML;
}

// SPRÁVNĚ: Vytváření elementů programaticky
function createUserCard(username, email) {
    const card = document.createElement('div');
    card.className = 'user-card';
    
    const nameElement = document.createElement('h3');
    nameElement.textContent = username; // BEZPEČNÉ
    
    const emailElement = document.createElement('p');
    emailElement.textContent = email; // BEZPEČNÉ
    
    card.appendChild(nameElement);
    card.appendChild(emailElement);
    
    return card;
}

// SPRÁVNĚ: Validace URL před redirectem
function redirectUser(url) {
    // BEZPEČNÉ: Whitelist povolených domén
    const allowedDomains = ['example.com', 'app.example.com'];
    
    try {
        const urlObj = new URL(url);
        
        if (allowedDomains.includes(urlObj.hostname)) {
            window.location.href = url;
        } else {
            console.error('Redirect na nepovolené domény není povolen');
        }
    } catch (e) {
        console.error('Neplatné URL');
    }
}

// SPRÁVNĚ: Bezpečné zpracování JSON
function processUserData(jsonString) {
    try {
        const data = JSON.parse(jsonString);
        
        // SPRÁVNĚ: Validace struktury a typů
        if (typeof data.username !== 'string' || 
            typeof data.email !== 'string') {
            throw new Error('Neplatná struktura dat');
        }
        
        // Další validace
        if (!data.email.includes('@')) {
            throw new Error('Neplatný email');
        }
        
        return data;
    } catch (e) {
        console.error('Chyba při zpracování dat:', e);
        return null;
    }
}

// SPRÁVNĚ: Environment variables místo hardcoded secrets
const API_ENDPOINT = process.env.API_ENDPOINT || 'https://api.example.com';
const API_KEY = process.env.API_KEY;

// SPRÁVNĚ: Bezpečné ukládání citlivých dat
function saveAuthToken(token) {
    // BEZPEČNÉ: sessionStorage pro krátkou dobu, ne localStorage
    // Ideálně použít HttpOnly cookies na backendu
    sessionStorage.setItem('auth_token', token);
}

// SPRÁVNĚ: CSRF token v API requestech
async function makeAuthenticatedRequest(endpoint, data) {
    const csrfToken = document.querySelector('meta[name="csrf-token"]').content;
    
    const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRF-Token': csrfToken
        },
        body: JSON.stringify(data),
        credentials: 'same-origin' // SPRÁVNĚ: Credentials pouze pro same-origin
    });
    
    return response.json();
}

// SPRÁVNĚ: Input validace
function validateUsername(username) {
    // Whitelist: pouze alfanumerické znaky a podtržítko
    const validPattern = /^[a-zA-Z0-9_]{3,20}$/;
    return validPattern.test(username);
}

function validateEmail(email) {
    // Základní email validace
    const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailPattern.test(email);
}

// Export pro použití v jiných modulech
module.exports = {
    displayUserMessage,
    displayRichContent,
    createUserCard,
    redirectUser,
    processUserData,
    validateUsername,
    validateEmail
};
