const { createProxyMiddleware } = require('http-proxy-middleware');

module.exports = function(app) {
  app.use(
    '/api',
    createProxyMiddleware({
      target: 'http://localhost:8000',
      changeOrigin: true,
      secure: false,
      // No pathRewrite needed - forward /api as is
      onError: (err, req, res) => {
        console.warn('Backend not available, skipping API proxy');
        res.status(200).json({ message: 'Backend not available' });
      },
      logLevel: 'debug',
      onProxyReq: (proxyReq, req, res) => {
        console.log('🔵 Proxy request:', req.method, req.url, '→', proxyReq.path);
      },
      onProxyRes: (proxyRes, req, res) => {
        console.log('🟢 Proxy response:', proxyRes.statusCode, req.url);
      }
    })
  );
}; 