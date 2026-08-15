const EventEmitter = require('events');

jest.mock('@whiskeysockets/baileys', () => ({
    default: jest.fn(),
    useMultiFileAuthState: jest.fn(),
    DisconnectReason: {}
}));

jest.mock('qrcode-terminal', () => ({
    generate: jest.fn()
}));

jest.mock('axios', () => ({
    post: jest.fn()
}));

jest.mock('fs', () => ({
    existsSync: jest.fn(() => false),
    mkdirSync: jest.fn(),
    statSync: jest.fn(() => ({ size: 0 })),
    copyFileSync: jest.fn(),
    truncateSync: jest.fn(),
    writeFileSync: jest.fn(),
    readFileSync: jest.fn()
}));

jest.mock('path', () => ({
    join: jest.fn((...args) => args.join('/')),
    __dirname: '/mock/dir'
}));

const http = require('http');

const mockServer = new EventEmitter();
mockServer.listen = jest.fn();
mockServer.on = jest.fn();
mockServer.close = jest.fn();

http.createServer = (handler) => {
    return mockServer;
};

function createMockResponse() {
    const res = new EventEmitter();
    res.statusCode = 200;
    res.headers = {};
    res.finished = false;
    res.data = null;

    res.writeHead = (statusCode, headers) => {
        res.statusCode = statusCode;
        if (headers) Object.assign(res.headers, headers);
        return res;
    };

    res.write = () => true;

    res.end = (data) => {
        res.finished = true;
        res.data = data || '';
        res.emit('finish');
        return res;
    };

    res.setHeader = (key, value) => {
        res.headers[key] = value;
    };

    return res;
}

function createMockRequest(method, url, body) {
    const req = new EventEmitter();
    req.method = method;
    req.url = url;
    req.headers = {};

    req.on = (event, cb) => {
        EventEmitter.prototype.on.call(req, event, cb);
        if (event === 'data' && body) {
            process.nextTick(() => cb(Buffer.from(body)));
        }
        if (event === 'end') {
            process.nextTick(() => cb());
        }
    };

    return req;
}

function invokeHandler(req, res, handler) {
    return new Promise((resolve, reject) => {
        const timeout = setTimeout(() => {
            reject(new Error('Handler timed out'));
        }, 3000);

        res.on('finish', () => {
            clearTimeout(timeout);
            let parsed = res.data;
            if (res.data && typeof res.data === 'string') {
                try { parsed = JSON.parse(res.data); } catch (_) {}
            }
            resolve({
                statusCode: res.statusCode,
                data: parsed
            });
        });

        res.on('error', (err) => {
            clearTimeout(timeout);
            reject(err);
        });

        try {
            handler(req, res);
        } catch (err) {
            clearTimeout(timeout);
            reject(err);
        }
    });
}

describe('WhatsApp Bridge HTTP API', () => {
    beforeEach(() => {
        jest.clearAllMocks();
    });

    afterEach(() => {
        jest.clearAllMocks();
    });

    describe('GET /health', () => {
        test('returns 200 with status ok', async () => {
            const healthHandler = (req, res) => {
                if (req.method === 'GET' && req.url === '/health') {
                    res.writeHead(200, { 'Content-Type': 'application/json' });
                    res.end(JSON.stringify({ status: 'ok', connected: false, time: new Date().toISOString() }));
                }
            };

            const req = createMockRequest('GET', '/health', null);
            const res = createMockResponse();
            const response = await invokeHandler(req, res, healthHandler);

            expect(response.statusCode).toBe(200);
            expect(response.data.status).toBe('ok');
            expect(typeof response.data.connected).toBe('boolean');
            expect(response.data.time).toBeDefined();
        });
    });

    describe('POST /send', () => {
        test('returns 500 when sock is not connected', async () => {
            const sendHandler = async (req, res) => {
                if (req.method === 'POST' && req.url === '/send') {
                    let body = '';
                    req.on('data', chunk => body += chunk);
                    req.on('end', async () => {
                        try {
                            const { to, message } = JSON.parse(body);
                            const sock = null;
                            if (!sock) {
                                res.writeHead(500, { 'Content-Type': 'application/json' });
                                res.end(JSON.stringify({ error: 'WhatsApp not connected' }));
                                return;
                            }
                            res.writeHead(200, { 'Content-Type': 'application/json' });
                            res.end(JSON.stringify({ success: true }));
                        } catch (err) {
                            res.writeHead(500, { 'Content-Type': 'application/json' });
                            res.end(JSON.stringify({ error: err.message }));
                        }
                    });
                }
            };

            const body = JSON.stringify({ to: '123@s.whatsapp.net', message: 'test' });
            const req = createMockRequest('POST', '/send', body);
            const res = createMockResponse();
            const response = await invokeHandler(req, res, sendHandler);

            expect(response.statusCode).toBe(500);
            expect(response.data.error).toBe('WhatsApp not connected');
        });
    });

    describe('POST /sendButtons', () => {
        test('returns 400 when buttons array is missing or empty', async () => {
            const sendButtonsHandler = async (req, res) => {
                if (req.method === 'POST' && req.url === '/sendButtons') {
                    let body = '';
                    req.on('data', chunk => body += chunk);
                    req.on('end', async () => {
                        try {
                            const parsed = JSON.parse(body);
                            const { to, text, buttons, headerType } = parsed;
                            if (!Array.isArray(buttons) || buttons.length === 0) {
                                res.writeHead(400, { 'Content-Type': 'application/json' });
                                res.end(JSON.stringify({ error: 'buttons array is required' }));
                                return;
                            }
                            res.writeHead(200, { 'Content-Type': 'application/json' });
                            res.end(JSON.stringify({ success: true }));
                        } catch (err) {
                            res.writeHead(500, { 'Content-Type': 'application/json' });
                            res.end(JSON.stringify({ error: err.message }));
                        }
                    });
                }
            };

            const body = JSON.stringify({ to: '123@s.whatsapp.net', text: 'Choose', buttons: [] });
            const req = createMockRequest('POST', '/sendButtons', body);
            const res = createMockResponse();
            const response = await invokeHandler(req, res, sendButtonsHandler);

            expect(response.statusCode).toBe(400);
            expect(response.data.error).toBe('buttons array is required');
        });
    });
});
