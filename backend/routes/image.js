import { Router } from 'express';
import { getOpenAI } from '../utils/openai.js';

const router = Router();

const BRAND_VISUAL_TONE = {
  'RZ Prime':        'sleek, dark-mode financial newsroom, deep blue and gold palette, cinematic editorial',
  'Coin Hall':       'modern crypto trading floor, green accents, data-driven, sharp professional',
  'ChainReporter':   'blockchain technology, teal and violet aurora aesthetic, futuristic journalism',
  'Meta Coin Guard': 'security-focused, dark red and black, cybersecurity intelligence, shield motifs',
};

router.post('/generate', async (req, res, next) => {
  try {
    const { article, platform, mediaBrand, sentiment, model = 'dall-e-3', size = '1792x1024' } = req.body;
    if (!article || !mediaBrand) return res.status(400).json({ error: 'Missing article or mediaBrand' });

    const tone     = BRAND_VISUAL_TONE[mediaBrand] || 'premium crypto news, dark cinematic aesthetic';
    const sentTone = sentiment === 'Bullish' ? 'optimistic upward energy, green tones'
                   : sentiment === 'Bearish' ? 'tense cautionary mood, red accents'
                   : 'balanced neutral editorial';

    const prompt = [
      `Hyper-realistic editorial photo illustration for a premium crypto news brand.`,
      `Story: ${article.title}.`,
      `Visual tone: ${tone}.`,
      `Mood: ${sentTone}.`,
      `Platform: ${platform} post — ${platform === 'Instagram' ? 'square-friendly, bold visual' : 'wide cinematic banner'}.`,
      `No text overlays. No logos. No people unless implied by silhouette.`,
      `Style: professional financial journalism photography, ultra-high-detail, dramatic lighting.`,
    ].join(' ');

    const openai = getOpenAI();

    const response = await openai.images.generate({
      model:   model === 'dall-e-2' ? 'dall-e-2' : 'dall-e-3',
      prompt,
      n: 1,
      size:    model === 'dall-e-2' ? '1024x1024' : size,
      quality: model === 'dall-e-3' ? 'hd' : 'standard',
    });

    const imageUrl = response.data[0].url;
    res.json({ imageUrl, prompt, model });
  } catch (err) {
    next(err);
  }
});

export default router;
