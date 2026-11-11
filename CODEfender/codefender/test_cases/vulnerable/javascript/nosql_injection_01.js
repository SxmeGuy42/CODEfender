/**
 * Testovací soubor: NoSQL Injection v Node.js + MongoDB
 */

const express = require('express');
const mongoose = require('mongoose');

const app = express();
app.use(express.json());

// NEBEZPEČNÉ: NoSQL Injection v MongoDB dotazu
app.post('/login', async (req, res) => {
    const { username, password } = req.body;
    
    // NOSQL INJECTION - uživatel může poslat {"$gt": ""}
    const user = await User.findOne({
        username: username,
        password: password
    });
    
    if (user) {
        res.json({ success: true, user });
    } else {
        res.json({ success: false });
    }
});

// NEBEZPEČNÉ: Prototype Pollution
function merge(target, source) {
    for (let key in source) {
        // Chybí kontrola __proto__ a constructor
        if (typeof source[key] === 'object') {
            target[key] = merge(target[key] || {}, source[key]);
        } else {
            target[key] = source[key];
        }
    }
    return target;
}

// NEBEZPEČNÉ: Chybějící rate limiting
app.post('/api/search', async (req, res) => {
    const query = req.body.query;
    
    // Žádný rate limit - možnost DoS útoku
    const results = await Database.find(query);
    res.json(results);
});

// NEBEZPEČNÉ: Chybějící autorizace
app.delete('/api/users/:id', async (req, res) => {
    const userId = req.params.id;
    
    // BROKEN ACCESS CONTROL - žádná kontrola oprávnění
    await User.findByIdAndDelete(userId);
    res.json({ success: true });
});

// NEBEZPEČNÉ: JWT bez expirace
const jwt = require('jsonwebtoken');
const SECRET = 'weak_secret_123'; // Slabý secret

function generateToken(user) {
    // Žádná expirace tokenu
    return jwt.sign({ userId: user._id }, SECRET);
}

module.exports = app;
