require('dotenv').config();
const express = require('express');
const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');
const path = require('path');

const app = express();
app.use(express.json());

const PORT = process.env.PORT || 3001;
const SESSION_DIR = path.join(__dirname, 'sessions');

let isClientReady = false;

const client = new Client({
    authStrategy: new LocalAuth({ dataPath: SESSION_DIR }),
    puppeteer: {
        args: ['--no-sandbox', '--disable-setuid-sandbox'],
    }
});

client.on('qr', (qr) => {
    console.log('QR RECEIVED. Scan the code below:');
    qrcode.generate(qr, { small: true });
    isClientReady = false;
});

client.on('ready', () => {
    console.log('Client is ready!');
    isClientReady = true;
});

client.on('authenticated', () => {
    console.log('AUTHENTICATED');
});

client.on('auth_failure', msg => {
    console.error('AUTHENTICATION FAILURE', msg);
    isClientReady = false;
});

client.on('disconnected', (reason) => {
    console.log('Client was logged out', reason);
    isClientReady = false;
    // Attempt to restart
    client.initialize().catch(console.error);
});

client.initialize().catch(err => {
    console.error("Failed to initialize client:", err);
});

// Health check endpoint
app.get('/health', (req, res) => {
    res.json({
        status: isClientReady ? 'UP' : 'DOWN'
    });
});

// Send message endpoint
app.post('/send', async (req, res) => {
    const { phone, message } = req.body;

    if (!phone || !message) {
        return res.status(400).json({ success: false, error: 'Phone and message are required' });
    }

    if (!isClientReady) {
        return res.status(503).json({ success: false, error: 'WhatsApp client is not ready' });
    }

    // Convert +919876543210 -> 919876543210@c.us
    const formattedPhone = phone.replace('+', '') + '@c.us';

    try {
        await client.sendMessage(formattedPhone, message);
        console.log(`Message sent to ${formattedPhone}`);
        res.json({ success: true });
    } catch (error) {
        console.error(`Failed to send message to ${formattedPhone}:`, error);
        res.status(500).json({ success: false, error: error.message });
    }
});

app.listen(PORT, () => {
    console.log(`WhatsApp Service is running on port ${PORT}`);
});
