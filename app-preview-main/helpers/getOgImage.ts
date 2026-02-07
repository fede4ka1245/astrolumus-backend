const puppeteer = require('puppeteer');

async function getOgImage(url: string) {
  const browser = await puppeteer.launch({
    executablePath: process.env.CHROME_BIN || null,
    args: ['--no-sandbox', '--headless', '--disable-gpu', '--disable-dev-shm-usage'],
    headless: true,
  });
  const page = await browser.newPage();
  await page.setViewportSize({ width: 612, height: 612 });
  await page.goto(url, { waitUntil: 'networkidle' });

  const buffer = await page.screenshot({
    type: 'jpeg',
    clip: { width: 500, height: 500, x: 56, y: 81 },
    quality: 50,
  });

  await browser.close();

  return 'data:image/jpeg;base64,' + buffer.toString('base64');
}

export default getOgImage;
