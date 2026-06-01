import { Router } from 'express';
import { callAppsScript } from '../utils/gsheets.js';

const router = Router();

// POST /api/sheets/approve
router.post('/approve', async (req, res, next) => {
  try {
    const result = await callAppsScript({ action: 'approve', ...req.body });
    res.json(result);
  } catch (err) {
    next(err);
  }
});

// POST /api/sheets/schedule
router.post('/schedule', async (req, res, next) => {
  try {
    const result = await callAppsScript({ action: 'schedule', ...req.body });
    res.json(result);
  } catch (err) {
    next(err);
  }
});

// POST /api/sheets/update
router.post('/update', async (req, res, next) => {
  try {
    const result = await callAppsScript({ action: 'update', ...req.body });
    res.json(result);
  } catch (err) {
    next(err);
  }
});

// POST /api/sheets/upload-image  — fetches DALL-E URL and saves to Drive via Apps Script
router.post('/upload-image', async (req, res, next) => {
  try {
    const result = await callAppsScript({ action: 'uploadImage', ...req.body });
    res.json(result);
  } catch (err) {
    next(err);
  }
});

export default router;
 