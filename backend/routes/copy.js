import { Router } from 'express';
import { getOpenAI } from '../utils/openai.js';

const router = Router();

const PLAT_RULES = {
  X: {
    maxChars: 280, maxTokens: 180, temperature: 0.20,
    system: (brand, sentiment) =>
      `You are the social media editor for ${brand}, a premium crypto news brand. Sentiment: ${sentiment}.\n` +
      `Write a single punchy news-wire tweet.\n` +
      `HARD RULE: response must be ≤ 280 characters total including spaces and hashtags.\n` +
      `Use 2-3 relevant hashtags. No emojis. Journalist tone. Start with the news hook.\n` +
      `Respond with JSON: { "copy": "...", "hashtags": ["#Tag1","#Tag2"] }`,
  },
  Telegram: {
    maxChars: 4096, maxTokens: 700, temperature: 0.28,
    system: (brand, sentiment) =>
      `You are the Telegram channel editor for ${brand}. Sentiment: ${sentiment}.\n` +
      `Write a full channel post: 2-4 paragraphs. Include context, implications, key figures.\n` +
      `End with a brand-voice closing line and 3-5 hashtags.\n` +
      `Respond with JSON: { "copy": "...", "hashtags": ["#Tag1"] }`,
  },
  Instagram: {
    maxChars: 2200, maxTokens: 700, temperature: 0.32,
    system: (brand, sentiment) =>
      `You are the Instagram editor for ${brand}. Sentiment: ${sentiment}.\n` +
      `Write a visual-first caption: strong opening hook, storytelling body, clear CTA.\n` +
      `Use 5-10 discovery hashtags at the end. Light use of relevant emojis.\n` +
      `Respond with JSON: { "copy": "...", "hashtags": ["#Tag1"] }`,
  },
};

router.post('/generate', async (req, res, next) => {
  try {
    const { article, platform, mediaBrand, sentiment } = req.body;
    if (!article || !platform || !mediaBrand) {
      return res.status(400).json({ error: 'Missing article, platform, or mediaBrand' });
    }

    const rule = PLAT_RULES[platform];
    if (!rule) return res.status(400).json({ error: `Unknown platform: ${platform}` });

    const userMsg = `Article title: ${article.title}\nSource: ${article.source}\nDescription: ${article.desc || ''}\nKeywords: ${(article.matchedKeywords || []).join(', ')}`;

    const openai = getOpenAI();
    let copy, hashtags;

    const call = async (extraInstruction = '') => {
      const completion = await openai.chat.completions.create({
        model: 'gpt-4o-mini',
        temperature: rule.temperature,
        max_tokens: rule.maxTokens,
        response_format: { type: 'json_object' },
        messages: [
          { role: 'system', content: rule.system(mediaBrand, sentiment || 'Neutral') + (extraInstruction ? '\n' + extraInstruction : '') },
          { role: 'user',   content: userMsg },
        ],
      });
      const parsed = JSON.parse(completion.choices[0].message.content);
      return { copy: parsed.copy || '', hashtags: parsed.hashtags || [] };
    };

    ({ copy, hashtags } = await call());

    // X retry if over limit
    if (platform === 'X' && copy.length > 280) {
      const over = copy.length;
      ({ copy, hashtags } = await call(`IMPORTANT: Your previous attempt was ${over} characters. You MUST fit within 280. Cut aggressively.`));
      if (copy.length > 280) copy = copy.slice(0, 277) + '…';
    }

    res.json({ copy, hashtags, charCount: copy.length, platform });
  } catch (err) {
    next(err);
  }
});

export default router;
