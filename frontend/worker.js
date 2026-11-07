export default {
  async fetch(request, env) {
    // One address only: https://rankspyseo.xyz (plain http and www redirect here)
    const url = new URL(request.url);
    if (url.protocol === 'http:' || url.hostname.startsWith('www.')) {
      url.protocol = 'https:';
      url.hostname = url.hostname.replace(/^www\./, '');
      return Response.redirect(url.toString(), 301);
    }

    let response = await env.ASSETS.fetch(request);

    // The SPA fallback answers every unknown path with index.html and a 200.
    // For paths that name a file (have an extension) that is a soft 404, so say 404.
    const { pathname } = new URL(request.url);
    const isFilePath = /\.[a-z0-9]{1,8}$/i.test(pathname) && !pathname.endsWith('.html');
    if (isFilePath && (response.headers.get('content-type') || '').includes('text/html')) {
      response = new Response('Not found', { status: 404, headers: { 'content-type': 'text/plain; charset=utf-8' } });
    }
    const newHeaders = new Headers(response.headers);

    newHeaders.set('Strict-Transport-Security', 'max-age=31536000; includeSubDomains; preload');
    newHeaders.set('X-Content-Type-Options', 'nosniff');
    newHeaders.set('X-Frame-Options', 'DENY');
    newHeaders.set('Referrer-Policy', 'strict-origin-when-cross-origin');
    newHeaders.set('X-XSS-Protection', '1; mode=block');
    newHeaders.set('Permissions-Policy', 'camera=(), microphone=(), geolocation=()');
    newHeaders.set(
      'Content-Security-Policy',
      [
        "default-src 'self'",
        "script-src 'self'",
        "style-src 'self' 'unsafe-inline'",
        "connect-src 'self' https://affectionate-recreation-production-e508.up.railway.app",
        "img-src 'self' data:",
        "font-src 'self'",
        "frame-ancestors 'none'",
      ].join('; ')
    );

    return new Response(response.body, {
      status: response.status,
      statusText: response.statusText,
      headers: newHeaders,
    });
  },
};
