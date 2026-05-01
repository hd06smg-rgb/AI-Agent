# 🤖 AI Agent Auto Trading Bot — OKX Futures

Bot trading otomatis yang menggunakan AI untuk menganalisis market dan mengeksekusi trade pada OKX Futures.

## 📊 Trading Pairs
- **BTC/USDT** Perpetual Futures
- **ETH/USDT** Perpetual Futures  
- **SOL/USDT** Perpetual Futures

## 🧠 AI Strategy
Bot menggunakan **confluence scoring** dari 3 indikator teknikal:

| Indikator | Fungsi |
|-----------|--------|
| **RSI (14)** | Detect overbought/oversold conditions |
| **MACD (12,26,9)** | Detect momentum & crossover signals |
| **SuperTrend (10,3)** | Detect trend direction |

### Logika AI:
1. Hitung skor setiap indikator (LONG=+1, SHORT=-1, NEUTRAL=0)
2. Minimum **2 dari 3** indikator harus setuju (confluence)
3. Evaluasi **Risk:Reward ratio** (minimum 1:2)
4. Jika semua kondisi terpenuhi → **EXECUTE TRADE**

## ⚙️ Konfigurasi

### Leverage & Margin
- Default leverage: **10x** (configurable per pair)
- Margin mode: **Isolated** (lebih aman)
- Max risk per trade: **2%** dari balance

### Risk Management
- Stop Loss: Based on **ATR** (Average True Range)
- Take Profit: Berdasarkan **R:R ratio** (min 1:2)
- Max daily loss: **6%** → bot berhenti trading
- Max open positions: **3** secara simultan

## 📱 Telegram Monitoring
Bot mengirim notifikasi real-time ke Telegram:
- 🟢 **Entry Signal** — Detail lengkap (pair, direction, SL, TP, leverage, R:R)
- 🔴 **Exit/Close** — P&L, reason (SL/TP hit)
- 📊 **Daily Summary** — Win rate, total P&L, balance
- 💓 **Heartbeat** — Status bot setiap jam
- ⚠️ **Error Alerts** — Jika terjadi error

## 🚀 Setup & Installation

### 1. Install Dependencies
```bash
cd ai-trading-bot
pip install -r requirements.txt
```

### 2. Konfigurasi API Keys
```bash
cp .env.example .env
```
Edit file `.env`:
```env
OKX_API_KEY=your_api_key
OKX_SECRET_KEY=your_secret_key
OKX_PASSPHRASE=your_passphrase
OKX_DEMO_MODE=True

TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

### 3. Cara Mendapatkan API Key OKX
1. Login ke [OKX](https://www.okx.com)
2. Pergi ke **Profile → API**
3. Buat API key baru dengan permission **Trade**
4. Simpan API Key, Secret Key, dan Passphrase

### 4. Cara Setup Telegram Bot
1. Chat [@BotFather](https://t.me/BotFather) di Telegram
2. Kirim `/newbot` dan ikuti instruksi
3. Simpan **Bot Token**
4. Chat [@userinfobot](https://t.me/userinfobot) untuk mendapatkan **Chat ID**

### 5. Jalankan Bot
```bash
python main.py
```

## 🖥️ Deploy ke VPS (24/7)

### Menggunakan systemd (Linux)
```bash
sudo nano /etc/systemd/system/trading-bot.service
```

Isi file:
```ini
[Unit]
Description=AI Trading Bot
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/path/to/ai-trading-bot
ExecStart=/usr/bin/python3 main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Aktifkan:
```bash
sudo systemctl daemon-reload
sudo systemctl enable trading-bot
sudo systemctl start trading-bot
```

Monitor:
```bash
sudo systemctl status trading-bot
journalctl -u trading-bot -f
```

### Menggunakan screen (Simple)
```bash
screen -S trading-bot
cd /path/to/ai-trading-bot
python main.py
# Tekan Ctrl+A lalu D untuk detach
```

Reconnect:
```bash
screen -r trading-bot
```

### Menggunakan Docker (Optional)
```bash
docker build -t trading-bot .
docker run -d --name trading-bot --restart always trading-bot
```

## ⚠️ DISCLAIMER
- Bot ini untuk **educational purposes**
- Crypto futures trading sangat **HIGH RISK**
- Selalu mulai dengan **DEMO MODE** (`OKX_DEMO_MODE=True`)
- **JANGAN** invest uang yang tidak siap anda kehilangan
- Past performance does NOT guarantee future results
- Anda bertanggung jawab penuh atas penggunaan bot ini

## 📁 Project Structure
```
ai-trading-bot/
├── config/
│   └── settings.py            # Semua konfigurasi
├── core/
│   ├── exchange.py            # OKX API wrapper
│   ├── data_fetcher.py        # Ambil data candle
│   ├── indicators.py          # RSI, MACD, SuperTrend
│   ├── ai_strategy.py         # AI signal scoring
│   ├── risk_manager.py        # Risk & position sizing
│   └── order_manager.py       # Execute & track orders
├── agents/
│   └── trading_agent.py       # Main trading loop
├── notifications/
│   └── telegram_bot.py        # Telegram alerts
├── utils/
│   └── logger.py              # Logging
├── logs/                       # Trade logs (auto-created)
├── main.py                    # Entry point
├── requirements.txt
├── .env.example
└── README.md
```
