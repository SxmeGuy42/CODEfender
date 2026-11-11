/**
 * Testovací soubor: Bezpečné API v Node.js + Express
 */

const express = require('express');
const mongoose = require('mongoose');
const bcrypt = require('bcrypt');
const jwt = require('jsonwebtoken');
const rateLimit = require('express-rate-limit');
const helmet = require('helmet');

const app = express();

// SPRÁVNĚ: Bezpečnostní middleware
app.use(helmet());
app.use(express.json({ limit: '10kb' })); // Limit velikosti requestu

// SPRÁVNĚ: Rate limiting
const limiter = rateLimit({
    windowMs: 15 * 60 * 1000, // 15 minut
    max: 100 // max 100 requestů na IP
});
app.use('/api/', limiter);

// SPRÁVNĚ: Ochrana proti NoSQL Injection
app.post('/login', async (req, res) => {
    const { username, password } = req.body;
    
    // SPRÁVNĚ: Validace typů
    if (typeof username !== 'string' || typeof password !== 'string') {
        return res.status(400).json({ error: 'Neplatné vstupy' });
    }
    
    // SPRÁVNĚ: Parametrizovaný dotaz s explicitními typy
    const user = await User.findOne({ 
        username: String(username)
    }).select('+password');
    
    if (!user) {
        return res.status(401).json({ error: 'Neplatné přihlašovací údaje' });
    }
    
    // SPRÁVNĚ: Bcrypt pro ověření hesla
    const isValid = await bcrypt.compare(password, user.password);
    
    if (isValid) {
        // SPRÁVNĚ: JWT s expirací
        const token = jwt.sign(
            { userId: user._id },
            process.env.JWT_SECRET,
            { expiresIn: '1h' }
        );
        
        res.json({ success: true, token });
    } else {
        res.status(401).json({ error: 'Neplatné přihlašovací údaje' });
    }
});

// SPRÁVNĚ: Autorizace middleware
function requireAuth(req, res, next) {
    const token = req.headers.authorization?.split(' ')[1];
    
    if (!token) {
        return res.status(401).json({ error: 'Chybí autentizace' });
    }
    
    try {
        const decoded = jwt.verify(token, process.env.JWT_SECRET);
        req.userId = decoded.userId;
        next();
    } catch (err) {
        return res.status(401).json({ error: 'Neplatný token' });
    }
}

// SPRÁVNĚ: Object-level authorization
app.delete('/api/users/:id', requireAuth, async (req, res) => {
    const userId = req.params.id;
    
    // SPRÁVNĚ: Kontrola oprávnění - uživatel může smazat pouze sebe
    if (req.userId !== userId) {
        return res.status(403).json({ error: 'Nedostatečná oprávnění' });
    }
    
    await User.findByIdAndDelete(userId);
    res.json({ success: true });
});

// SPRÁVNĚ: Input sanitizace a validace
app.post('/api/search', requireAuth, async (req, res) => {
    const { query } = req.body;
    
    // Validace
    if (typeof query !== 'string' || query.length > 100) {
        return res.status(400).json({ error: 'Neplatný dotaz' });
    }
    
    // SPRÁVNĚ: Použití bezpečných MongoDB operátorů
    const results = await Database.find({
        $text: { $search: query }
    }).limit(50);
    
    res.json(results);
});

// SPRÁVNĚ: Bezpečné generování JWT
function generateToken(user) {
    // SPRÁVNĚ: Silný secret z environment variables + expirace
    const secret = process.env.JWT_SECRET;
    
    if (!secret || secret.length < 32) {
        throw new Error('JWT_SECRET musí být nastaven a dostatečně dlouhý');
    }
    
    return jwt.sign(
        { 
            userId: user._id,
            username: user.username 
        },
        secret,
        { 
            expiresIn: '1h',
            algorithm: 'HS256'
        }
    );
}

// SPRÁVNĚ: Hashování hesel při registraci
app.post('/api/register', async (req, res) => {
    const { username, email, password } = req.body;
    
    // Validace
    if (!username || !email || !password) {
        return res.status(400).json({ error: 'Všechna pole jsou povinná' });
    }
    
    if (password.length < 8) {
        return res.status(400).json({ error: 'Heslo musí mít alespoň 8 znaků' });
    }
    
    // SPRÁVNĚ: Bcrypt pro hashování
    const saltRounds = 12;
    const passwordHash = await bcrypt.hash(password, saltRounds);
    
    const user = new User({
        username: String(username),
        email: String(email),
        password: passwordHash
    });
    
    try {
        await user.save();
        res.status(201).json({ success: true });
    } catch (err) {
        res.status(400).json({ error: 'Uživatel již existuje' });
    }
});

// SPRÁVNĚ: Error handling bez odhalení detailů
app.use((err, req, res, next) => {
    console.error(err.stack); // Log na serveru
    
    // SPRÁVNĚ: Obecná chybová zpráva pro klienta
    res.status(500).json({ 
        error: 'Interní chyba serveru'
        // Neodhalovat stack trace nebo detaily
    });
});

module.exports = app;
