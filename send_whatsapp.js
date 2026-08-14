const axios = require('axios');
const readline = require('readline');

const SEND_API_URL = 'http://localhost:5057/send';

function getArgs() {
    const args = process.argv.slice(2);
    const result = { to: null, message: null };
    for (let i = 0; i < args.length; i++) {
        if (args[i] === '--to' && args[i + 1]) result.to = args[++i];
        if (args[i] === '--message' && args[i + 1]) result.message = args[++i];
    }
    return result;
}

async function sendMessage() {
    const { to, message } = getArgs();
    if (!to || !message) {
        console.log('Usage: node send_whatsapp.js --to "+254712345678" --message "Hello"');
        process.exit(1);
    }

    try {
        const response = await axios.post(SEND_API_URL, {
            to: to,
            message: message
        });
        if (response.data.success) {
            console.log(`✅ Message sent to ${to}`);
        } else {
            console.error('❌ Failed:', response.data.error);
            process.exit(1);
        }
    } catch (err) {
        console.error('❌ Error sending message:', err.message);
        if (err.code === 'ECONNREFUSED') {
            console.log('Make sure bot.js is running first.');
        }
        process.exit(1);
    }
}

sendMessage();
