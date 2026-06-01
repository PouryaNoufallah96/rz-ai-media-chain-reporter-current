import 'dotenv/config';
import express from 'express';
import cors from 'cors';
import copyRoutes  from './routes/copy.js';
import imageRoutes from './routes/image.js';
import sheetsRoutes from './routes/sheets.js';

const app  = express();
const PORT = process.env.PORT || 3001;

app.use(cors({ origin: process.env.FRONTEND_ORIGIN || 'http://localhost:3000' }));
app.use(express.json({ limit: '10mb' }));

app.use('/api/copy',   copyRoutes);
app.use('/api/image',  imageRoutes);
app.use('/api/sheets', sheetsRoutes);

app.get('/api/health', (_req, res) => res.json({ ok: true, ts: Date.now() }));

app.use((err, _req, res, _next) => {
  console.error('[ERROR]', err.message);
  res.status(500).json({ error: err.message || 'Internal server error' });
});

app.listen(PORT, () => console.log(`ChainReporter backend → http://localhost:${PORT}`));
