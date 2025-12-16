const express = require('express')
const cors = require('cors')
const axios = require('axios')
const sqlite3 = require('sqlite3').verbose()
const path = require('path')

const app = express()
app.use(cors())
app.use(express.json())
app.use(express.static(path.join(__dirname, '..', 'public')))

const DB_PATH = path.join(__dirname, '..', '..', 'trading_bot.db')
const db = new sqlite3.Database(DB_PATH)

db.serialize(() => {
  db.run(
    `CREATE TABLE IF NOT EXISTS futures_tickers (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      symbol TEXT UNIQUE,
      price REAL,
      price_change REAL,
      volume_24h REAL,
      last_updated TEXT
    )`
  )
  db.run(
    `CREATE TABLE IF NOT EXISTS futures_analysis (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      symbol TEXT NOT NULL,
      timeframe TEXT NOT NULL,
      timestamp TEXT NOT NULL,
      current_price REAL,
      price_change REAL,
      rsi REAL,
      macd REAL,
      macd_signal REAL,
      macd_hist REAL,
      ma REAL,
      ma_signal INTEGER,
      volume REAL,
      volume_ma REAL,
      volume_ratio REAL,
      total_score REAL,
      signal TEXT
    )`
  )
})

async function fetchTickers() {
  const url = 'https://api.bitunix.com/fapi/v1/ticker/24hr'
  const { data } = await axios.get(url, { timeout: 15000 })
  return Array.isArray(data) ? data : [data]
}

async function upsertTickers(items) {
  const now = new Date().toISOString()
  const stmt = db.prepare(
    `INSERT INTO futures_tickers (symbol, price, price_change, volume_24h, last_updated)
     VALUES (?, ?, ?, ?, ?)
     ON CONFLICT(symbol) DO UPDATE SET
       price=excluded.price,
       price_change=excluded.price_change,
       volume_24h=excluded.volume_24h,
       last_updated=excluded.last_updated`
  )
  for (const t of items) {
    const symbol = String(t.symbol || '')
    if (!symbol.endsWith('USDT')) continue
    const price = Number(t.lastPrice ?? t.price ?? 0)
    const change = Number(t.priceChangePercent ?? t.priceChange ?? 0)
    const vol = Number(t.quoteVolume ?? t.volume ?? 0)
    stmt.run(symbol, price, change, vol, now)
  }
  stmt.finalize()
}

async function syncTickers() {
  try {
    const tickers = await fetchTickers()
    await upsertTickers(tickers)
    return tickers.length
  } catch (e) {
    return 0
  }
}

function mapInterval(iv) {
  const m = { '1': '1m', '3': '3m', '5': '5m', '15': '15m', '30': '30m', '60': '1h', '240': '4h', D: '1d', '1m': '1m', '15m': '15m', '1h': '1h', '4h': '4h', '1d': '1d' }
  return m[String(iv)] || String(iv)
}

async function fetchKlines(symbol, interval, limit = 200) {
  const url = 'https://api.bitunix.com/fapi/v1/klines'
  const params = { symbol, interval: mapInterval(interval), limit }
  const { data } = await axios.get(url, { params, timeout: 15000 })
  return Array.isArray(data) ? data : []
}

function mean(arr) {
  if (!arr.length) return 0
  let s = 0
  for (const v of arr) s += v
  return s / arr.length
}

function computeIndicators(closes, volumes) {
  const { RSI, MACD } = require('technicalindicators')
  const rsiArr = RSI.calculate({ values: closes, period: 14 })
  const rsi = rsiArr.length ? rsiArr[rsiArr.length - 1] : 50
  const macdArr = MACD.calculate({ values: closes, fastPeriod: 12, slowPeriod: 26, signalPeriod: 9, SimpleMAOscillator: false, SimpleMASignal: false })
  const lastMacd = macdArr.length ? macdArr[macdArr.length - 1] : { MACD: 0, signal: 0, histogram: 0 }
  const ma = closes.length >= 20 ? mean(closes.slice(-20)) : mean(closes)
  const volMa = volumes.length >= 20 ? mean(volumes.slice(-20)) : mean(volumes)
  const currentVol = volumes.length ? volumes[volumes.length - 1] : 0
  const volumeRatio = volMa === 0 ? 1 : currentVol / volMa
  const oldPrice = closes.length >= 2 ? closes[closes.length - 2] : closes[closes.length - 1]
  const newPrice = closes.length ? closes[closes.length - 1] : 0
  const priceChange = oldPrice ? ((newPrice - oldPrice) / oldPrice) * 100 : 0
  let maSignal = 0
  if (newPrice > ma * 1.02) maSignal = 1
  else if (newPrice < ma * 0.98) maSignal = -1
  let rsiScore = 0
  if (rsi < 30) rsiScore = ((30 - rsi) / 30) * 50
  else if (rsi > 70) rsiScore = -((rsi - 70) / 30) * 50
  const macdScore = (lastMacd.histogram || 0) * 10
  const priceScore = priceChange * 2
  let volumeScore = -15
  if (volumeRatio > 1.5) volumeScore = 30
  else if (volumeRatio > 1.0) volumeScore = 15
  else if (volumeRatio > 0.5) volumeScore = 0
  const maScore = maSignal * 20
  const totalScore = rsiScore * 0.25 + macdScore * 0.25 + priceScore * 0.25 + volumeScore * 0.15 + maScore * 0.1
  let signal = 'NEUTRAL'
  if (totalScore > 20) signal = 'STRONG_BUY'
  else if (totalScore > 10) signal = 'BUY'
  else if (totalScore <= -20) signal = 'STRONG_SELL'
  else if (totalScore < -10) signal = 'SELL'
  return { rsi, macd: { macd: lastMacd.MACD || 0, signal: lastMacd.signal || 0, histogram: lastMacd.histogram || 0 }, ma, maSignal, volume: currentVol, volumeMa: volMa, volumeRatio, priceChange, currentPrice: newPrice, totalScore, signal }
}

function storeAnalysis(a) {
  const stmt = db.prepare(
    `INSERT INTO futures_analysis (symbol, timeframe, timestamp, current_price, price_change, rsi, macd, macd_signal, macd_hist, ma, ma_signal, volume, volume_ma, volume_ratio, total_score, signal)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`
  )
  stmt.run(
    a.symbol,
    a.timeframe,
    a.timestamp,
    a.current_price,
    a.price_change,
    a.rsi,
    a.macd.macd,
    a.macd.signal,
    a.macd.histogram,
    a.ma,
    a.ma_signal,
    a.volume,
    a.volume_ma,
    a.volume_ratio,
    a.score.total_score,
    a.signal
  )
  stmt.finalize()
}

app.get('/api/futures/tickers', (req, res) => {
  const limit = Math.min(parseInt(req.query.limit || '100'), 1000)
  db.all('SELECT symbol, price, price_change, volume_24h, last_updated FROM futures_tickers ORDER BY volume_24h DESC LIMIT ?', [limit], (err, rows) => {
    if (err) return res.status(500).json({ error: String(err) })
    res.json({ symbols: rows, total: rows.length })
  })
})

app.post('/api/futures/sync', async (req, res) => {
  try {
    const count = await syncTickers()
    res.json({ success: true, synced: count })
  } catch (e) {
    res.status(500).json({ error: String(e) })
  }
})

app.get('/api/futures/klines', async (req, res) => {
  try {
    const symbol = String(req.query.symbol || '')
    const interval = String(req.query.interval || '15m')
    const limit = parseInt(req.query.limit || '200')
    if (!symbol) return res.status(400).json({ error: 'symbol required' })
    const kl = await fetchKlines(symbol, interval, limit)
    const out = kl.map(k => ({ time: Number(k[0]), open: Number(k[1]), high: Number(k[2]), low: Number(k[3]), close: Number(k[4]), volume: Number(k[5]) }))
    res.json({ klines: out })
  } catch (e) {
    res.status(500).json({ error: String(e) })
  }
})

app.get('/api/futures/analyze', async (req, res) => {
  try {
    const timeframes = String(req.query.timeframes || '15m,1m,1d').split(',')
    const minVolume = Number(req.query.min_volume || 1000000)
    const limit = parseInt(req.query.limit || '50')
    const minScoreRaw = req.query.min_score
    db.all('SELECT symbol, volume_24h FROM futures_tickers WHERE volume_24h >= ? ORDER BY volume_24h DESC', [minVolume], async (err, rows) => {
      if (err) return res.status(500).json({ error: String(err) })
      let symbols = rows.map(r => ({ symbol: r.symbol, volume_24h: r.volume_24h }))
      if (!symbols.length) {
        try {
          const t = await fetchTickers()
          const filtered = []
          for (const x of t) {
            const sym = String(x.symbol || '')
            if (!sym.endsWith('USDT')) continue
            const vol = Number(x.quoteVolume ?? x.volume ?? 0)
            if (vol >= minVolume) filtered.push({ symbol: sym, volume_24h: vol })
          }
          symbols = filtered
        } catch {}
      }
      symbols.sort((a, b) => b.volume_24h - a.volume_24h)
      const analyzed = []
      for (const s of symbols.slice(0, 100)) {
        const tfResults = {}
        for (const tf of timeframes) {
          const kl = await fetchKlines(s.symbol, tf, 500)
          if (!kl || !kl.length) continue
          const closes = kl.map(k => Number(k[4]))
          const volumes = kl.map(k => Number(k[5]))
          const ind = computeIndicators(closes, volumes)
          const score = { total_score: ind.totalScore }
          const analysis = {
            symbol: s.symbol,
            timeframe: tf,
            current_price: ind.currentPrice,
            price_change: ind.priceChange,
            rsi: ind.rsi,
            macd: ind.macd,
            ma: ind.ma,
            ma_signal: ind.maSignal,
            volume: ind.volume,
            volume_ma: ind.volumeMa,
            volume_ratio: ind.volumeRatio,
            score,
            signal: ind.signal,
            timestamp: new Date().toISOString()
          }
          tfResults[tf] = analysis
          storeAnalysis(analysis)
        }
        if (Object.keys(tfResults).length) {
          const avg = Object.values(tfResults).reduce((acc, a) => acc + a.score.total_score, 0) / Object.keys(tfResults).length
          analyzed.push({ symbol: s.symbol, volume_24h: s.volume_24h, timeframes: tfResults, avg_score: avg })
        }
      }
      if (minScoreRaw !== undefined) {
        const ms = Number(minScoreRaw)
        if (!isNaN(ms)) symbols = symbols
        analyzed.splice(0, analyzed.length, ...analyzed.filter(x => x.avg_score >= ms))
      }
      analyzed.sort((a, b) => b.avg_score - a.avg_score)
      res.json({ symbols: analyzed.slice(0, limit), total: analyzed.length })
    })
  } catch (e) {
    res.status(500).json({ error: String(e) })
  }
})

app.get('/api/futures/analyze-symbol', async (req, res) => {
  try {
    const symbol = String(req.query.symbol || '')
    const timeframe = String(req.query.timeframe || '15m')
    if (!symbol) return res.status(400).json({ error: 'symbol required' })
    const kl = await fetchKlines(symbol, timeframe, 500)
    if (!kl || !kl.length) return res.status(404).json({ error: 'no data' })
    const closes = kl.map(k => Number(k[4]))
    const volumes = kl.map(k => Number(k[5]))
    const ind = computeIndicators(closes, volumes)
    const result = {
      symbol,
      timeframe,
      current_price: ind.currentPrice,
      price_change: ind.priceChange,
      rsi: ind.rsi,
      macd: ind.macd,
      ma: ind.ma,
      ma_signal: ind.maSignal,
      volume: ind.volume,
      volume_ma: ind.volumeMa,
      volume_ratio: ind.volumeRatio,
      score: { total_score: ind.totalScore },
      signal: ind.signal,
      timestamp: new Date().toISOString()
    }
    storeAnalysis(result)
    res.json(result)
  } catch (e) {
    res.status(500).json({ error: String(e) })
  }
})

app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, '..', 'public', 'index.html'))
})

const PORT = process.env.PORT ? Number(process.env.PORT) : 3001
app.listen(PORT, () => {
  console.log(`Node service running at http://localhost:${PORT}`)
})

setTimeout(() => { syncTickers() }, 0)
setInterval(() => { syncTickers() }, 60000)
