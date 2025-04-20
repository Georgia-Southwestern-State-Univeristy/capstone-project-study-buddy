const express = require('express');
const path = require('path');

const app = express();
const port = process.env.PORT || 8080;

// Add cache control middleware
app.use((req, res, next) => {
  // For HTML files - no caching
  if (req.path.endsWith('.html') || req.path === '/') {
    res.setHeader('Cache-Control', 'no-cache, no-store, must-revalidate');
    res.setHeader('Pragma', 'no-cache');
    res.setHeader('Expires', '0');
  } 
  // For JS, CSS, and other static assets - short cache time
  else if (req.path.match(/\.(js|css|png|jpg|jpeg|gif|ico|svg)$/)) {
    res.setHeader('Cache-Control', 'public, max-age=3600'); // 1 hour
  }
  next();
});

// Serve static files from the dist directory
app.use(express.static(path.join(__dirname, 'dist/meme-mingle')));

// Redirect all other routes to index.html
app.get('*', (req, res) => {
  res.sendFile(path.join(__dirname, 'dist/meme-mingle/index.html'));
});

app.listen(port, () => {
  console.log(`Server running on http://localhost:${port}`);
});