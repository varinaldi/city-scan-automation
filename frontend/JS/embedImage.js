// JS/embedImage.js

export function embedImage(data, config = {}) {
  const {
    url,
    widthPercent = 100,
    heightPercent = null,
    attribution = null
  } = config;

  if (!url) {
    throw new Error('URL is required for embedded image');
  }

  // Create container div
  const container = document.createElement('div');
  container.style.position = 'relative';
  container.style.display = 'inline-block';
  container.style.maxWidth = '100%';
  container.style.maxHeight = '100%';
  container.style.paddingBottom = '20px';

  // Set width as percentage, clamped to 100%
  const clampedWidth = Math.min(widthPercent, 100);
  container.style.width = `${clampedWidth}%`;

  // Create image element
  const img = document.createElement('img');
  img.src = url;
  img.style.display = 'block';
  img.style.width = '100%';
  img.style.maxWidth = '100%';
  img.style.maxHeight = '100%';

  // Set height as percentage if provided
  if (heightPercent) {
    const clampedHeight = Math.min(heightPercent, 100);
    img.style.height = `${clampedHeight}%`;
  }

  img.style.objectFit = 'contain';

  // Create attribution element if provided
  if (attribution) {
    const attr = document.createElement('div');
    attr.textContent = attribution;
    attr.style.position = 'absolute';
    attr.style.bottom = '0px';
    attr.style.right = '-8px';
    attr.style.fontSize = '8px';
    attr.style.color = '#666';
    attr.style.backgroundColor = 'rgba(255, 255, 255, 0.9)';
    attr.style.padding = '2px 8px';
    attr.style.borderRadius = '2px';
    container.appendChild(attr);
  }

  container.appendChild(img);

  return container;
}
