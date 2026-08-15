const {
    default: makeWASocket,
    useMultiFileAuthState,
    DisconnectReason
} = require('@whiskeysockets/baileys');
const { Boom } = require('@hapi/boom');
const qrcode = require('qrcode-terminal');
const axios = require('axios');
const http = require('http');
const fs = require('fs');
const path = require('path');

const FLASK_HANDLER_URL = 'http://localhost:5056/webhook';
const SEND_API_PORT = 5057;
const AUTH_DIR = path.join(__dirname, 'auth_info_baileys');
const PERSONA_FILE = path.join(__dirname, 'hermes_persona.txt');
const TYPING_DELAY_BASE = 1500;
const TYPING_DELAY_PER_CHAR = 8;
const TYPING_DELAY_MAX = 3000;
const MAX_LOG_BYTES = 10 * 1024 * 1024;

let sock = null;

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

function rotateLog(filePath) {
    try {
        if (fs.existsSync(filePath) && fs.statSync(filePath).size > MAX_LOG_BYTES) {
            const bak = filePath + '.1';
            if (fs.existsSync(bak)) fs.unlinkSync(bak);
            fs.copyFileSync(filePath, bak);
            fs.truncateSync(filePath, 0);
        }
    } catch (_) {
        // best-effort
    }
}

async function sendWithTyping(sock, jid, text) {
    const chars = text.length;
    const delay = Math.min(
        TYPING_DELAY_BASE + (chars * TYPING_DELAY_PER_CHAR),
        TYPING_DELAY_MAX
    );
    try {
        await sock.sendPresenceUpdate('composing', jid);
    } catch (_) {}
    await sleep(delay);
    await sock.sendMessage(jid, { text });
}

async function sendReaction(sock, jid, messageKey, emoji) {
    try {
        await sock.sendMessage(jid, {
            react: {
                text: emoji,
                key: messageKey
            }
        });
    } catch (_) {
        // reactions are best-effort
    }
}

async function markRead(sock, jid, messageKey) {
    try {
        await sock.sendMessage(jid, {
            readReceipts: {
                messageId: messageKey.id,
                senderJid: messageKey.remoteJid,
                receiverJid: jid
            }
        });
    } catch (_) {
        // read receipts are best-effort
    }
}

async function connectToWhatsApp() {
    if (!fs.existsSync(AUTH_DIR)) {
        fs.mkdirSync(AUTH_DIR, { recursive: true });
    }

    const { state, saveCreds } = await useMultiFileAuthState(AUTH_DIR);

    sock = makeWASocket({
        auth: state,
        printQRInTty: true,
        browser: ['Mac OS', 'Chrome', '120.0.0.0'],
        syncFullHistory: true,
        getMessage: async (key) => {
            return { conversation: 'Hello from JARVIS Bridge' };
        }
    });

    sock.ev.on('creds.update', saveCreds);

    sock.ev.on('connection.update', async (update) => {
        const { connection, lastDisconnect, qr, isNewLogin } = update;
        rotateLog(path.join(__dirname, 'logs', 'baileysbot-stdout.log'));
        console.log('[connection.update]', JSON.stringify({ connection, hasQr: !!qr, hasLastDisconnect: !!lastDisconnect, isNewLogin }));
        if (qr) {
            console.log('');
            console.log('QR CODE — Scan with WhatsApp → Linked Devices → Link a Device');
            console.log('');
            qrcode.generate(qr, { small: true });
            try {
                const qrFile = path.join(AUTH_DIR, 'qr.txt');
                fs.writeFileSync(qrFile, qr, 'utf-8');
            } catch (e) {
                console.log('Could not save QR to file:', e.message);
            }
        }
        if (isNewLogin) {
            console.log('New login detected, saving credentials...');
        }
        if (connection === 'open') {
            console.log('WhatsApp Bridge connected successfully!');
            try {
                await sock.sendPresenceUpdate('available');
            } catch (_) {}
            if (!sock.user) {
                try {
                    const code = await sock.requestPairingCode();
                    console.log('Pairing code:', code);
                } catch (e) {
                    console.log('Pairing code request failed:', e.message);
                }
            }
        }
        if (connection === 'close') {
            const err = lastDisconnect?.error;
            const status = err?.output?.statusCode;
            const data = err?.data;
            console.log('Connection closed. Reconnecting in 3s...', { status, data, hasErr: !!err });
            if (err?.output?.statusCode !== 401) setTimeout(() => connectToWhatsApp(), 3000);
        }
    });

    sock.ev.on('qr', (qr) => {
        console.log('');
        console.log('QR CODE (ev) — Scan with WhatsApp → Linked Devices → Link a Device');
        console.log('');
        qrcode.generate(qr, { small: true });
        try {
            const qrFile = path.join(AUTH_DIR, 'qr.txt');
            fs.writeFileSync(qrFile, qr, 'utf-8');
        } catch (e) {
            console.log('Could not save QR to file:', e.message);
        }
    });

    sock.ev.on('messages.upsert', async ({ messages, type }) => {
        if (type !== 'notify') return;
        const msg = messages[0];
        if (!msg.message || msg.key.fromMe) return;
        const sender = msg.key.remoteJid;
        if (sender.endsWith('@newsletter')) {
            console.log(`Ignoring newsletter message from ${sender}`);
            return;
        }

        const messageText = msg.message.conversation ||
                           msg.message.extendedTextMessage?.text ||
                           (msg.message.imageMessage && msg.message.imageMessage.caption) ||
                           (msg.message.videoMessage && msg.message.videoMessage.caption) ||
                           (msg.message.documentMessage && msg.message.documentMessage.caption) ||
                           "[Non-text message]";

        console.log(`Message from ${sender}: ${messageText.substring(0, 120)}`);

        if (msg.key.id) {
            await markRead(sock, sender, msg.key);
        }

        try {
            const response = await axios.post(FLASK_HANDLER_URL, {
                message: messageText,
                sender: sender
            });

            const replyText = response.data.reply;
            if (!replyText) {
                console.log(`No reply for ${sender}`);
                return;
            }

            const emoji = replyText.startsWith('✅') ? '👍' :
                          replyText.startsWith('❌') ? '👎' :
                          replyText.includes('logged') || replyText.includes('Saved') ? '✅' :
                          replyText.includes('Pending') ? '⏳' : '💬';

            await sendWithTyping(sock, sender, replyText);
            console.log(`Reply sent to ${sender}`);

            if (msg.key.id && emoji) {
                await sendReaction(sock, sender, msg.key, emoji);
            }

        } catch (error) {
            console.error('Error:', error.message);
            console.error('Code:', error.code);
            console.error('Stack:', error.stack);
            try {
                await sendWithTyping(sock, sender, 'Sorry, I am having trouble reaching the brain. Try again in a moment.');
            } catch (sendErr) {
                console.error('Failed to send fallback message:', sendErr.message);
            }
        }
    });

    sock.ev.on('group-participants.update', async (update) => {
        const { groupId, participants, action } = update;
        console.log(`Group ${groupId}: ${action} ${participants.join(', ')}`);
    });
}

const sendServer = http.createServer(async (req, res) => {
    if (req.method === 'POST' && req.url === '/send') {
        let body = '';
        req.on('data', chunk => body += chunk);
        req.on('end', async () => {
            try {
                const { to, message } = JSON.parse(body);
                const sendErrors = [];
                if (!to || typeof to !== 'string' || to.trim() === '') {
                    sendErrors.push({ field: 'to', message: 'to must be a non-empty string' });
                }
                if (!message || typeof message !== 'string' || message.trim() === '') {
                    sendErrors.push({ field: 'message', message: 'message must be a non-empty string' });
                }
                if (sendErrors.length > 0) {
                    res.writeHead(400, { 'Content-Type': 'application/json' });
                    res.end(JSON.stringify({ error: 'validation failed', details: sendErrors }));
                    return;
                }
                if (!sock) {
                    res.writeHead(500, { 'Content-Type': 'application/json' });
                    res.end(JSON.stringify({ error: 'WhatsApp not connected' }));
                    return;
                }
                await sock.sendMessage(to, { text: message });
                res.writeHead(200, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ success: true }));
            } catch (err) {
                res.writeHead(500, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ error: err.message }));
            }
        });
    } else if (req.method === 'POST' && req.url === '/sendButtons') {
        let body = '';
        req.on('data', chunk => body += chunk);
        req.on('end', async () => {
            try {
                const { to, text, buttons, headerType } = JSON.parse(body);
                const btnErrors = [];
                if (!to || typeof to !== 'string' || to.trim() === '') {
                    btnErrors.push({ field: 'to', message: 'to must be a non-empty string' });
                }
                if (text !== undefined && text !== null && typeof text === 'string' && text.length > 1000) {
                    btnErrors.push({ field: 'text', message: 'text must be at most 1000 characters' });
                }
                if (!Array.isArray(buttons) || buttons.length < 1 || buttons.length > 3) {
                    btnErrors.push({ field: 'buttons', message: 'buttons must be an array with 1-3 items' });
                }
                if (btnErrors.length > 0) {
                    res.writeHead(400, { 'Content-Type': 'application/json' });
                    res.end(JSON.stringify({ error: 'validation failed', details: btnErrors }));
                    return;
                }
                if (!sock) {
                    res.writeHead(500, { 'Content-Type': 'application/json' });
                    res.end(JSON.stringify({ error: 'WhatsApp not connected' }));
                    return;
                }
                if (!Array.isArray(buttons) || buttons.length === 0) {
                    res.writeHead(400, { 'Content-Type': 'application/json' });
                    res.end(JSON.stringify({ error: 'buttons array is required' }));
                    return;
                }
                const formattedButtons = buttons.map(b => ({
                    type: 'reply',
                    reply: {
                        id: b.buttonParams?.id || b.buttonText?.displayText || 'btn',
                        title: b.buttonText?.displayText || 'Option'
                    }
                }));
                await sock.sendMessage(to, {
                    text: text || 'Choose an option:',
                    footer: 'JARVIS',
                    buttons: formattedButtons,
                    headerType: headerType || 1
                });
                res.writeHead(200, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ success: true }));
            } catch (err) {
                res.writeHead(500, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ error: err.message }));
            }
        });
    } else if (req.method === 'GET' && req.url === '/health') {
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ status: 'ok', connected: !!sock, time: new Date().toISOString() }));
    } else {
        res.writeHead(404);
        res.end('Not found');
    }
});

sendServer.on('error', (err) => {
    if (err.code === 'EADDRINUSE') {
        console.error(`Send API port ${SEND_API_PORT} already in use. Another instance may be running.`);
        process.exit(1);
    }
});

sendServer.listen(SEND_API_PORT, () => {
    console.log(`Send API listening on http://localhost:${SEND_API_PORT}/send`);
    console.log(`Health check at http://localhost:${SEND_API_PORT}/health`);
});

process.on('SIGINT', () => {
    console.log('\nShutting down...');
    if (sock) sock.end();
    process.exit(0);
});

process.on('SIGTERM', () => {
    console.log('\nShutting down...');
    if (sock) sock.end();
    process.exit(0);
});

process.on('uncaughtException', (err) => {
    console.error('Uncaught exception:', err);
});

process.on('unhandledRejection', (err) => {
    console.error('Unhandled rejection:', err);
});

console.log('Starting JARVIS WhatsApp Bridge...');
connectToWhatsApp().catch(err => console.error('Fatal Error:', err));
