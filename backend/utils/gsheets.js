import fetch from 'node-fetch';

const SCRIPT_URL = () => {
  const url = process.env.GOOGLE_APPS_SCRIPT_URL;
  if (!url || url.startsWith('PASTE_')) throw new Error('GOOGLE_APPS_SCRIPT_URL not configured in .env');
  return url;
};

export async function callAppsScript(payload) {
  const res = await fetch(SCRIPT_URL(), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
    redirect: 'follow',
  });

  if (!res.ok) throw new Error(`Apps Script HTTP ${res.status}`);
  const data = await res.json();
  if (!data.success) throw new Error(data.error || 'Apps Script returned failure');
  return data;
}
