const fs = require('fs');
const path = require('path');
const sharp = require('sharp');

async function convertAll() {
  const dir = path.join(__dirname);
  const files = fs.readdirSync(dir).filter(f => f.endsWith('.svg'));
  for (const file of files) {
    const inPath = path.join(dir, file);
    const outName = file.replace(/\.svg$/i, '.png');
    const outPath = path.join(dir, outName);
    try {
      await sharp(inPath)
        .png({ compressionLevel: 9 })
        .toFile(outPath);
      console.log('Converted', file, '->', outName);
    } catch (err) {
      console.error('Failed converting', file, err.message);
    }
  }
}

convertAll();
